"""Tests for health spans: starting, stopping, and integrations that failed."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import CoreState, HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.honeycomb.const import DOMAIN

from .common import ENTRY_DATA, TRACES_URL, attributes, sent_spans


async def test_start_and_failed_integrations(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(TRACES_URL)
    MockConfigEntry(domain="example_broken", state=ConfigEntryState.SETUP_RETRY).add_to_hass(hass)
    hass.set_state(CoreState.not_running)
    entry = MockConfigEntry(domain=DOMAIN, unique_id="example-team/home", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    await entry.runtime_data.async_flush()

    start, broken = sent_spans(aioclient_mock)
    assert start["name"] == "homeassistant start"
    assert attributes(start)["ha.type"] == "health"
    assert "ha.version" in attributes(start)
    assert broken["name"] == "example_broken setup_retry"
    assert attributes(broken)["ha.integration"] == "example_broken"


async def test_added_while_running(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    """Set up after Home Assistant started, there is no start to measure."""
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    assert [span["name"] for span in sent_spans(aioclient_mock)] == ["homeassistant stop"]
