"""Tests for state spans: how long each state lasted."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.honeycomb.otlp import unix_nano

from .common import attributes, sent_spans


async def _spans(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> list[dict]:
    await entry.runtime_data.async_flush()
    return sent_spans(aioclient_mock)


async def test_state_span(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    hass.states.async_set("light.example_kitchen", "on", {"friendly_name": "Example Kitchen"})
    on = hass.states.get("light.example_kitchen")
    freezer.tick(timedelta(minutes=42))
    hass.states.async_set("light.example_kitchen", "off", {"friendly_name": "Example Kitchen"})
    off = hass.states.get("light.example_kitchen")

    [span] = await _spans(hass, entry, aioclient_mock)
    assert span["name"] == "light on"
    assert span["startTimeUnixNano"] == str(unix_nano(on.last_changed))
    assert span["endTimeUnixNano"] == str(unix_nano(off.last_changed))
    assert int(span["endTimeUnixNano"]) - int(span["startTimeUnixNano"]) == 42 * 60 * 10**9
    assert attributes(span) == {
        "ha.type": "state",
        "ha.entity_id": "light.example_kitchen",
        "ha.domain": "light",
        "ha.state": "on",
        "ha.next_state": "off",
        "ha.friendly_name": "Example Kitchen",
    }


async def test_no_span_without_an_ended_state(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    hass.states.async_set("light.example_kitchen", "on", {"brightness": 100})
    hass.states.async_set("light.example_kitchen", "on", {"brightness": 200})
    hass.states.async_remove("light.example_kitchen")
    assert await _spans(hass, entry, aioclient_mock) == []


async def test_numeric_state(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    sensor = {"unit_of_measurement": "°C", "device_class": "temperature"}
    hass.states.async_set("sensor.example_outdoor_temperature", "12.5", sensor)
    hass.states.async_set("sensor.example_outdoor_temperature", "nan", sensor)
    hass.states.async_set("sensor.example_outdoor_temperature", "13", sensor)

    first, second = await _spans(hass, entry, aioclient_mock)
    # Named by the kind of value, not the value, so that span names stay few.
    assert first["name"] == "sensor temperature"
    assert attributes(first) == {
        "ha.type": "state",
        "ha.entity_id": "sensor.example_outdoor_temperature",
        "ha.domain": "sensor",
        "ha.state": "12.5",
        "ha.next_state": "nan",
        "ha.device_class": "temperature",
        "ha.unit": "°C",
        "ha.value": 12.5,
    }
    assert "ha.value" not in attributes(second)


async def test_unavailable(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    hass.states.async_set("light.example_kitchen", "unavailable")
    hass.states.async_set("light.example_kitchen", "off")
    [span] = await _spans(hass, entry, aioclient_mock)
    assert span["name"] == "light unavailable"
    assert attributes(span)["ha.state"] == "unavailable"


@pytest.mark.parametrize(
    ("context", "has_context_id"),
    [
        (Context(user_id="example-user-id"), True),
        (Context(parent_id="example-parent-id"), True),
        (Context(), False),
    ],
)
async def test_context(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    context: Context,
    has_context_id: bool,
) -> None:
    hass.states.async_set("light.example_kitchen", "off")
    hass.states.async_set("light.example_kitchen", "on", context=context)
    hass.states.async_set("light.example_kitchen", "off")
    ended, began = await _spans(hass, entry, aioclient_mock)
    # The change in this context ended the first state and began the second.
    assert attributes(ended).get("ha.next_context.id") == (context.id if has_context_id else None)
    assert attributes(began).get("ha.context.id") == (context.id if has_context_id else None)
    assert "ha.next_context.id" not in attributes(began)


@pytest.mark.parametrize(
    ("state", "attributes_", "name"),
    [
        ("1180.2", {"device_class": "power"}, "sensor power"),
        ("42", {}, "sensor value"),
        ("washing", {"device_class": "enum"}, "sensor washing"),
        ("unavailable", {"device_class": "power"}, "sensor unavailable"),
    ],
)
async def test_value_names(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    state: str,
    attributes_: dict,
    name: str,
) -> None:
    hass.states.async_set("sensor.example_washer", state, attributes_)
    hass.states.async_set("sensor.example_washer", "0", attributes_)
    [span] = await _spans(hass, entry, aioclient_mock)
    assert span["name"] == name


async def test_area_and_floor(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    area_registry: ar.AreaRegistry,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    floor_registry: fr.FloorRegistry,
) -> None:
    floor = floor_registry.async_create("Ground Floor")
    kitchen = area_registry.async_create("Example Kitchen", floor_id=floor.floor_id)
    hall = area_registry.async_create("Example Hall")
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("example", "1")}
    )
    device_registry.async_update_device(device.id, area_id=hall.id)
    by_entity = entity_registry.async_get_or_create(
        "light", "example", "1", suggested_object_id="example_pendant", device_id=device.id
    )
    # An entity on a device has an area of its own only if it has a name of its own.
    entity_registry.async_update_entity(by_entity.entity_id, area_id=kitchen.id, name="Example Pendant")
    by_device = entity_registry.async_get_or_create(
        "light", "example", "2", suggested_object_id="example_lamp", device_id=device.id
    )
    nowhere = entity_registry.async_get_or_create(
        "light", "example", "3", suggested_object_id="example_spare"
    )

    for entity_id in (by_entity.entity_id, by_device.entity_id, nowhere.entity_id):
        hass.states.async_set(entity_id, "on")
        hass.states.async_set(entity_id, "off")

    places = [
        {key: value for key, value in attributes(span).items() if key in ("ha.area", "ha.floor")}
        for span in await _spans(hass, entry, aioclient_mock)
    ]
    assert places == [
        {"ha.area": "Example Kitchen", "ha.floor": "Ground Floor"},
        {"ha.area": "Example Hall"},
        {},
    ]


@pytest.mark.parametrize(
    ("entity_id", "states", "attrs"),
    [
        ("device_tracker.example_phone", ("home", "not_home"), {}),
        ("person.example_person", ("home", "not_home"), {}),
        ("zone.example_work", ("0", "1"), {}),
        ("camera.example_porch", ("idle", "streaming"), {}),
        ("image.example_snapshot", ("2026-01-01", "2026-01-02"), {}),
        ("sensor.example_heart_rate", ("60", "61"), {}),
        ("sensor.example_band_reading", ("60", "61"), {"unit_of_measurement": "bpm"}),
        ("sensor.example_daily_steps", ("100", "200"), {}),
        ("sensor.example_blood_pressure_systolic", ("120", "121"), {}),
        ("binary_sensor.example_bed_asleep", ("off", "on"), {}),
    ],
)
async def test_excluded_by_default(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    entity_id: str,
    states: tuple[str, str],
    attrs: dict[str, Any],
) -> None:
    for state in states:
        hass.states.async_set(entity_id, state, attrs)
    assert await _spans(hass, entry, aioclient_mock) == []


async def test_phone_sensors_excluded_by_default(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    entity_registry: er.EntityRegistry,
) -> None:
    phone = entity_registry.async_get_or_create(
        "sensor", "mobile_app", "1", suggested_object_id="example_phone_battery_level"
    )
    hass.states.async_set(phone.entity_id, "80")
    hass.states.async_set(phone.entity_id, "79")
    assert await _spans(hass, entry, aioclient_mock) == []


@pytest.mark.parametrize(
    "entity_id",
    ["switch.example_tv_sleep_timer", "sensor.example_meter_pulse_count", "sensor.example_rain_rate"],
)
async def test_not_excluded(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker, entity_id: str
) -> None:
    hass.states.async_set(entity_id, "1")
    hass.states.async_set(entity_id, "2")
    assert len(await _spans(hass, entry, aioclient_mock)) == 1


async def test_sent_every_ten_seconds(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    # The clock is frozen before the integration starts its timer.
    hass.states.async_set("light.example_kitchen", "on")
    hass.states.async_set("light.example_kitchen", "off")
    await hass.async_block_till_done()
    assert sent_spans(aioclient_mock) == []
    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert len(sent_spans(aioclient_mock)) == 1


async def test_sent_when_home_assistant_stops(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    hass.states.async_set("light.example_kitchen", "on")
    hass.states.async_set("light.example_kitchen", "off")
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    assert [span["name"] for span in sent_spans(aioclient_mock)] == ["light on", "homeassistant stop"]


async def test_sent_on_unload(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    hass.states.async_set("light.example_kitchen", "on")
    hass.states.async_set("light.example_kitchen", "off")
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert len(sent_spans(aioclient_mock)) == 1
    hass.states.async_set("light.example_kitchen", "on")
    await hass.async_block_till_done()
    assert len(sent_spans(aioclient_mock)) == 1


async def test_device(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("example", "1")},
        name="Example Bulb",
        manufacturer="Example Devices",
        model="Example Bulb Mk 2",
    )
    light = entity_registry.async_get_or_create("light", "example", "1", device_id=device.id)
    hass.states.async_set(light.entity_id, "on")
    hass.states.async_set(light.entity_id, "off")
    [span] = await _spans(hass, entry, aioclient_mock)
    assert {
        key: value
        for key, value in attributes(span).items()
        if key.startswith(("ha.device", "ha.integration"))
    } == {
        "ha.integration": "example",
        "ha.device": "Example Bulb",
        "ha.device.manufacturer": "Example Devices",
        "ha.device.model": "Example Bulb Mk 2",
    }


async def test_activity(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    thermostat = "climate.example_thermostat"
    readings = {"current_temperature": 19.5, "temperature": 21}
    hass.states.async_set(thermostat, "heat", {"hvac_action": "idle", **readings})
    freezer.tick(timedelta(minutes=5))
    hass.states.async_set(thermostat, "heat", {"hvac_action": "heating", **readings})
    freezer.tick(timedelta(minutes=12))
    hass.states.async_set(
        thermostat, "heat", {"hvac_action": "heating", **readings, "current_temperature": 21.2}
    )
    freezer.tick(timedelta(minutes=1))
    hass.states.async_set(
        thermostat, "heat", {"hvac_action": "idle", **readings, "current_temperature": 21.3}
    )

    # The first change starts the clock: when the idle period before it began is not known.
    [span] = await _spans(hass, entry, aioclient_mock)
    assert span["name"] == "climate heating"
    assert int(span["endTimeUnixNano"]) - int(span["startTimeUnixNano"]) == 13 * 60 * 10**9
    assert attributes(span) == {
        "ha.type": "activity",
        "ha.entity_id": thermostat,
        "ha.domain": "climate",
        "ha.state": "heat",
        "ha.activity": "heating",
        "ha.next_activity": "idle",
        "ha.current_temperature": 21.2,
        "ha.temperature": 21.0,
    }
