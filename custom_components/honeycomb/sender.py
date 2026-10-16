"""Sending spans to Honeycomb: batched, at least every 10 seconds, never making Home Assistant wait.

Spans wait in a bounded queue. If Honeycomb cannot be reached they stay there for the next attempt,
and when the queue is full the oldest are dropped first (okf/spec/01-telemetry.md, 1.6).
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from datetime import datetime, timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from .const import HEADER_API_KEY, REGIONS, SCOPE_NAME
from .otlp import AttributeValue, Span, encode_request

_LOGGER = logging.getLogger(__name__)

FLUSH_INTERVAL = timedelta(seconds=10)
MAX_BATCH = 1000
MAX_QUEUE = 10_000
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


class SpanSender:
    """Queues spans and posts them to Honeycomb's OTLP endpoint."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        api_key: str,
        region: str,
        resource: dict[str, AttributeValue],
        scope_version: str,
    ) -> None:
        self._hass = hass
        self._session = async_get_clientsession(hass)
        self._url = f"{REGIONS[region]}/v1/traces"
        self._headers = {HEADER_API_KEY: api_key}
        self._resource = resource
        self._scope_version = scope_version
        self._queue: deque[Span] = deque()
        self._lock = asyncio.Lock()
        self._unreachable = False
        self._dropped = 0

    @property
    def queued(self) -> int:
        """How many spans are waiting to be sent."""
        return len(self._queue)

    @callback
    def async_start(self, entry: ConfigEntry) -> None:
        """Send every interval, and once more when Home Assistant stops."""
        entry.async_on_unload(
            async_track_time_interval(
                self._hass, self._async_send_on_interval, FLUSH_INTERVAL, cancel_on_shutdown=True
            )
        )
        # Not listen_once: removing a one-time listener after it has fired logs an error on unload.
        entry.async_on_unload(self._hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, self._async_send_on_stop))

    @callback
    def add(self, span: Span) -> None:
        """Queue a span; send at once if a batch is full."""
        if len(self._queue) >= MAX_QUEUE:
            self._queue.popleft()
            self._count_dropped(1)
        self._queue.append(span)
        if len(self._queue) >= MAX_BATCH and not self._lock.locked():
            self._hass.async_create_background_task(self.async_flush(), "honeycomb send")

    async def _async_send_on_interval(self, _now: datetime) -> None:
        await self.async_flush()

    async def _async_send_on_stop(self, _event: Event) -> None:
        await self.async_flush()

    async def async_flush(self) -> None:
        """Send everything queued, a batch at a time, until done or Honeycomb fails."""
        async with self._lock:
            while self._queue:
                batch = [self._queue.popleft() for _ in range(min(MAX_BATCH, len(self._queue)))]
                if not await self._async_post(batch):
                    self._requeue(batch)
                    return

    def _requeue(self, batch: list[Span]) -> None:
        """Put a batch back at the front, dropping its oldest spans if the queue has filled."""
        room = MAX_QUEUE - len(self._queue)
        keep = batch[len(batch) - room :] if room < len(batch) else batch
        if len(keep) < len(batch):
            self._count_dropped(len(batch) - len(keep))
        self._queue.extendleft(reversed(keep))

    async def _async_post(self, batch: list[Span]) -> bool:
        """Post a batch. False if it should be tried again later."""
        body = encode_request(batch, self._resource, SCOPE_NAME, self._scope_version)
        try:
            async with self._session.post(
                self._url, json=body, headers=self._headers, timeout=REQUEST_TIMEOUT
            ) as resp:
                if resp.status in (408, 429) or resp.status >= 500:
                    self._set_unreachable(f"HTTP {resp.status}")
                    return False
                if resp.status >= 400:
                    _LOGGER.error(
                        "Honeycomb refused %d spans (HTTP %d): %s", len(batch), resp.status, await resp.text()
                    )
                    return True
        except (aiohttp.ClientError, TimeoutError) as err:
            self._set_unreachable(repr(err))
            return False
        self._set_reachable()
        return True

    def _set_unreachable(self, reason: str) -> None:
        if not self._unreachable:
            _LOGGER.warning("Cannot send to Honeycomb (%s); spans are queued and will be retried", reason)
            self._unreachable = True

    def _set_reachable(self) -> None:
        if self._unreachable:
            _LOGGER.info("Sending to Honeycomb again")
            self._unreachable = False
        if self._dropped:
            _LOGGER.info("%d spans were dropped while the queue was full", self._dropped)
            self._dropped = 0

    def _count_dropped(self, count: int) -> None:
        if not self._dropped:
            _LOGGER.warning("More than %d spans are waiting to be sent; dropping the oldest", MAX_QUEUE)
        self._dropped += count
