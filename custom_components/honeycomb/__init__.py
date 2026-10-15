"""Honeycomb: traces of what happens in a home, sent to Honeycomb.

The integration reads only Home Assistant's public interfaces: the event bus, the state machine
and the registries. What becomes a span is specified in okf/spec/01-telemetry.md.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

type HoneycombConfigEntry = ConfigEntry[None]


async def async_setup_entry(hass: HomeAssistant, entry: HoneycombConfigEntry) -> bool:
    """Set up Honeycomb from a config entry. Nothing is sent yet."""
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HoneycombConfigEntry) -> bool:
    """Unload a config entry."""
    return True
