"""Tests for the Honeycomb config flow."""

from __future__ import annotations

import aiohttp
import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.honeycomb.const import CONF_REGION, CONF_SERVICE_NAME, DOMAIN

AUTH_URL = "https://api.honeycomb.io/1/auth"
INPUT = {CONF_API_KEY: "test-key", CONF_REGION: "us", CONF_SERVICE_NAME: "home-assistant"}
AUTH_OK = {
    "team": {"name": "Example Team", "slug": "example-team"},
    "environment": {"name": "Home", "slug": "home"},
}


async def _submit(hass: HomeAssistant, user_input: dict) -> dict:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


async def test_creates_entry(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(AUTH_URL, json=AUTH_OK)
    result = await _submit(hass, INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Example Team / Home"
    assert result["data"] == INPUT
    assert result["result"].unique_id == "example-team/home"
    assert aioclient_mock.mock_calls[0][3]["X-Honeycomb-Team"] == "test-key"


async def test_eu_region(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get("https://api.eu1.honeycomb.io/1/auth", json=AUTH_OK)
    result = await _submit(hass, {**INPUT, CONF_REGION: "eu"})
    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    ("mock", "error"),
    [
        ({"status": 401}, "invalid_auth"),
        ({"status": 500}, "cannot_connect"),
        ({"exc": aiohttp.ClientConnectionError()}, "cannot_connect"),
        ({"exc": TimeoutError()}, "cannot_connect"),
    ],
)
async def test_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, mock: dict, error: str
) -> None:
    aioclient_mock.get(AUTH_URL, **mock)
    result = await _submit(hass, INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_already_configured(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id="example-team/home", data=INPUT).add_to_hass(hass)
    aioclient_mock.get(AUTH_URL, json=AUTH_OK)
    result = await _submit(hass, INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_setup_and_unload(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id="example-team/home", data=INPUT)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is config_entries.ConfigEntryState.LOADED
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is config_entries.ConfigEntryState.NOT_LOADED
