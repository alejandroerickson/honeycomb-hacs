"""Tests for the options: what the user leaves out, sends anyway, and allows as attributes."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import area_registry as ar, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.honeycomb.const import (
    CONF_ATTRIBUTES,
    CONF_EXCLUDE,
    CONF_EXCLUDE_AREAS,
    CONF_EXCLUDE_DEVICE_CLASSES,
    CONF_INCLUDE,
    DOMAIN,
)

from .common import ENTRY_DATA, TRACES_URL, attributes, sent_spans


async def _setup(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, options: dict[str, Any]
) -> MockConfigEntry:
    aioclient_mock.post(TRACES_URL)
    entry = MockConfigEntry(domain=DOMAIN, unique_id="example-team/home", data=ENTRY_DATA, options=options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _sent(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> dict[str, dict]:
    """The state spans sent, by entity id."""
    await hass.async_block_till_done()
    await entry.runtime_data.async_flush()
    return {
        attributes(span)["ha.entity_id"]: span
        for span in sent_spans(aioclient_mock)
        if attributes(span).get("ha.type") == "state"
    }


def _change(hass: HomeAssistant, entity_id: str, attrs: dict | None = None) -> None:
    hass.states.async_set(entity_id, "on", attrs)
    hass.states.async_set(entity_id, "off", attrs)


async def test_options_flow(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    choices = {
        CONF_EXCLUDE: ["sensor.*_power"],
        CONF_EXCLUDE_AREAS: [],
        CONF_EXCLUDE_DEVICE_CLASSES: ["energy"],
        CONF_INCLUDE: ["device_tracker.example_phone"],
        CONF_ATTRIBUTES: ["brightness"],
    }
    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input=choices)
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == choices
    assert entry.state is ConfigEntryState.LOADED


async def test_exclude(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    entry = await _setup(
        hass,
        aioclient_mock,
        {CONF_EXCLUDE: ["sensor.*_power"], CONF_EXCLUDE_DEVICE_CLASSES: ["energy"]},
    )
    _change(hass, "sensor.example_fridge_power")
    _change(hass, "sensor.example_meter", {"device_class": "energy"})
    _change(hass, "sensor.example_temperature")
    assert set(await _sent(hass, entry, aioclient_mock)) == {"sensor.example_temperature"}


async def test_exclude_area(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    area_registry: ar.AreaRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    garage = area_registry.async_create("Example Garage")
    light = entity_registry.async_get_or_create("light", "example", "garage")
    entity_registry.async_update_entity(light.entity_id, area_id=garage.id)
    entry = await _setup(hass, aioclient_mock, {CONF_EXCLUDE_AREAS: [garage.id]})
    _change(hass, light.entity_id)
    _change(hass, "light.example_kitchen")
    assert set(await _sent(hass, entry, aioclient_mock)) == {"light.example_kitchen"}


async def test_include(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """What stays home by default is sent when included by name, unless also left out."""
    entry = await _setup(
        hass,
        aioclient_mock,
        {CONF_INCLUDE: ["device_tracker.example_*", "person.example_avery"], CONF_EXCLUDE: ["person.*"]},
    )
    _change(hass, "device_tracker.example_phone")
    _change(hass, "device_tracker.other_phone")
    _change(hass, "person.example_avery")
    assert set(await _sent(hass, entry, aioclient_mock)) == {"device_tracker.example_phone"}


async def test_attributes(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    entry = await _setup(hass, aioclient_mock, {CONF_ATTRIBUTES: ["brightness", "effect_list", "missing"]})
    _change(
        hass, "light.example_kitchen", {"brightness": 128, "effect_list": ["rainbow"], "color_mode": "xy"}
    )
    span = (await _sent(hass, entry, aioclient_mock))["light.example_kitchen"]
    sent = {key: value for key, value in attributes(span).items() if key.startswith("ha.attr.")}
    assert sent == {"ha.attr.brightness": 128, "ha.attr.effect_list": '["rainbow"]'}
