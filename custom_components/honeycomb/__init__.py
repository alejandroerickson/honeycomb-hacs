"""Honeycomb: traces of what happens in a home, sent to Honeycomb.

The integration reads only Home Assistant's public interfaces: the event bus, the state machine
and the registries. What becomes a span is specified in okf/spec/01-telemetry.md.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import CONF_REGION, CONF_SERVICE_NAME, DOMAIN
from .contexts import ContextTracer
from .filters import Rules
from .health import async_track_health
from .sender import SpanSender
from .states import StateTracker

type HoneycombConfigEntry = ConfigEntry[SpanSender]


async def async_setup_entry(hass: HomeAssistant, entry: HoneycombConfigEntry) -> bool:
    """Set up Honeycomb from a config entry: start sending."""
    integration = await async_get_integration(hass, DOMAIN)
    sender = SpanSender(
        hass,
        api_key=entry.data[CONF_API_KEY],
        region=entry.data[CONF_REGION],
        resource={"service.name": entry.data[CONF_SERVICE_NAME]},
        scope_version=str(integration.version),
    )
    entry.runtime_data = sender
    # The options flow reloads the entry when the user's choices change.
    rules = Rules.from_options(entry.options)
    contexts = ContextTracer(hass, sender, rules)
    for unsub in [
        *await contexts.async_start(),
        StateTracker(hass, sender, contexts, rules).async_start(),
        *async_track_health(hass, sender),
    ]:
        entry.async_on_unload(unsub)
    # Last, so the health span for stopping is queued before the final send.
    sender.async_start(entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HoneycombConfigEntry) -> bool:
    """Unload a config entry, sending what is queued first."""
    await entry.runtime_data.async_flush()
    return True
