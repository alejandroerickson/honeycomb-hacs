"""Shared fixtures."""

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.honeycomb.const import DOMAIN

from .common import ENTRY_DATA, TRACES_URL


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load the integration from custom_components/."""


@pytest.fixture
async def entry(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> MockConfigEntry:
    """The integration, set up, with Honeycomb accepting every request."""
    aioclient_mock.post(TRACES_URL)
    entry = MockConfigEntry(domain=DOMAIN, unique_id="example-team/home", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
