"""Home Assistant's health: how long it took to start, when it stopped, and integrations that failed.

okf/spec/01-telemetry.md, 1.4.
"""

from __future__ import annotations

from datetime import datetime

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_HOMEASSISTANT_STOP,
    __version__ as HA_VERSION,
)
from homeassistant.core import CALLBACK_TYPE, CoreState, Event, HomeAssistant, callback

from .otlp import AttributeValue, Span
from .sender import SpanSender

FAILED = (ConfigEntryState.SETUP_ERROR, ConfigEntryState.SETUP_RETRY, ConfigEntryState.MIGRATION_ERROR)


@callback
def async_track_health(hass: HomeAssistant, sender: SpanSender) -> list[CALLBACK_TYPE]:
    """Send health spans; return the functions that stop it."""

    def span(name: str, start: datetime, end: datetime, attributes: dict[str, AttributeValue]) -> Span:
        return Span(name, start, end, {"ha.type": "health", "ha.version": HA_VERSION, **attributes})

    started_at: list[datetime] = []

    @callback
    def starting(event: Event) -> None:
        started_at.append(event.time_fired)

    @callback
    def started(event: Event) -> None:
        now = event.time_fired
        sender.add(span("homeassistant start", started_at[0] if started_at else now, now, {}))
        for entry in hass.config_entries.async_entries():
            if entry.state in FAILED:
                sender.add(
                    span(
                        f"{entry.domain} {entry.state.value}",
                        now,
                        now,
                        {"ha.integration": entry.domain, "ha.entry_state": entry.state.value},
                    )
                )

    @callback
    def stopping(event: Event) -> None:
        sender.add(span("homeassistant stop", event.time_fired, event.time_fired, {}))

    # Each fires once; listen_once is not used because removing one that has fired logs an error.
    unsubs = [hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, stopping)]
    # Set up while Home Assistant starts, rather than added to one already running.
    if hass.state in (CoreState.not_running, CoreState.starting):
        unsubs.append(hass.bus.async_listen(EVENT_HOMEASSISTANT_START, starting))
        unsubs.append(hass.bus.async_listen(EVENT_HOMEASSISTANT_STARTED, started))
    return unsubs
