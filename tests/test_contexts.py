"""Tests for context traces: runs, people's actions, service calls and how devices responded."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import Context, HomeAssistant, ServiceCall
from homeassistant.helpers import area_registry as ar, entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .common import attributes, sent_spans

LIGHT = "light.example_kitchen"


def _respond(hass: HomeAssistant, *, ignore: tuple[str, ...] = ()) -> None:
    """Fake light services: each targeted light changes in the call's context, unless ignored."""

    async def handle(call: ServiceCall) -> None:
        entity_ids = call.data.get("entity_id", [])
        for entity_id in [entity_ids] if isinstance(entity_ids, str) else entity_ids:
            if entity_id not in ignore:
                state = "off" if call.service == "turn_off" else "on"
                hass.states.async_set(entity_id, state, context=call.context)

    for service in ("turn_on", "turn_off", "toggle"):
        hass.services.async_register("light", service, handle)


async def _spans(
    entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker, hass: HomeAssistant
) -> list[dict]:
    await hass.async_block_till_done()
    await entry.runtime_data.async_flush()
    return sent_spans(aioclient_mock)


def _by_type(spans: list[dict], kind: str) -> list[dict]:
    return [span for span in spans if attributes(span).get("ha.type") == kind]


async def _person(hass: HomeAssistant) -> Context:
    user = await hass.auth.async_create_user("Example Person")
    await hass.async_block_till_done()
    return Context(user_id=user.id)


async def test_person_action(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    _respond(hass)
    hass.states.async_set(LIGHT, "off")
    context = await _person(hass)
    await hass.services.async_call("light", "turn_on", {"entity_id": LIGHT}, blocking=True, context=context)

    spans = await _spans(entry, aioclient_mock, hass)
    [action] = _by_type(spans, "action")
    [response] = _by_type(spans, "response")
    assert action["name"] == "light.turn_on"
    assert "parentSpanId" not in action
    assert attributes(action) == {
        "ha.type": "action",
        "ha.service": "light.turn_on",
        "ha.domain": "light",
        "ha.context.id": context.id,
        "ha.targets": 1,
        "ha.user": "Example Person",
        "ha.effect": "changed",
        "ha.changed": 1,
    }
    assert response["name"] == "light → on"
    assert response["traceId"] == action["traceId"]
    assert response["parentSpanId"] == action["spanId"]
    assert attributes(response)["ha.effect"] == "changed"
    assert attributes(response)["ha.previous_state"] == "off"
    assert attributes(response)["ha.same_context"] is True

    [state] = _by_type(spans, "state")
    assert attributes(state)["ha.cause"] == "person"
    assert attributes(state)["ha.user"] == "Example Person"


async def test_no_effect(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    _respond(hass, ignore=(LIGHT,))
    hass.states.async_set(LIGHT, "off")
    context = await _person(hass)
    await hass.services.async_call("light", "turn_on", {"entity_id": LIGHT}, blocking=True, context=context)
    assert _by_type(await _spans(entry, aioclient_mock, hass), "action") == []

    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    spans = await _spans(entry, aioclient_mock, hass)
    [action] = _by_type(spans, "action")
    [response] = _by_type(spans, "response")
    assert attributes(action)["ha.effect"] == "none"
    assert attributes(action)["ha.none"] == 1
    assert response["name"] == "light → no effect"
    assert attributes(response)["ha.effect"] == "none"
    assert int(response["endTimeUnixNano"]) - int(response["startTimeUnixNano"]) == 60 * 10**9


@pytest.mark.parametrize(("state", "effect"), [("on", "already"), ("unavailable", "unavailable")])
async def test_nothing_to_wait_for(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker, state: str, effect: str
) -> None:
    _respond(hass, ignore=(LIGHT,))
    hass.states.async_set(LIGHT, state)
    context = await _person(hass)
    await hass.services.async_call("light", "turn_on", {"entity_id": LIGHT}, blocking=True, context=context)
    spans = await _spans(entry, aioclient_mock, hass)
    [action] = _by_type(spans, "action")
    assert attributes(action)["ha.effect"] == effect
    assert _by_type(spans, "response") == []


async def test_area_target(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    area_registry: ar.AreaRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    kitchen = area_registry.async_create("Example Kitchen")
    lights = []
    for number in (1, 2):
        light = entity_registry.async_get_or_create("light", "example", str(number))
        entity_registry.async_update_entity(light.entity_id, area_id=kitchen.id)
        hass.states.async_set(light.entity_id, "off")
        lights.append(light.entity_id)

    async def handle(call: ServiceCall) -> None:
        for entity_id in lights:
            hass.states.async_set(entity_id, "on", context=call.context)

    hass.services.async_register("light", "turn_on", handle)
    context = await _person(hass)
    await hass.services.async_call(
        "light", "turn_on", {"area_id": kitchen.id}, blocking=True, context=context
    )
    spans = await _spans(entry, aioclient_mock, hass)
    [action] = _by_type(spans, "action")
    assert attributes(action)["ha.targets"] == 2
    assert sorted(attributes(span)["ha.entity_id"] for span in _by_type(spans, "response")) == sorted(lights)
    assert {attributes(span)["ha.area"] for span in _by_type(spans, "response")} == {"Example Kitchen"}


async def test_not_followed(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    """A call by neither a person nor a followed run, and one at a left-out entity, send nothing."""
    _respond(hass)
    hass.states.async_set(LIGHT, "off")
    await hass.services.async_call("light", "turn_on", {"entity_id": LIGHT}, blocking=True, context=Context())
    hass.states.async_set("device_tracker.example_phone", "home")
    hass.services.async_register("device_tracker", "see", lambda call: None)
    context = await _person(hass)
    await hass.services.async_call(
        "device_tracker", "see", {"entity_id": "device_tracker.example_phone"}, blocking=True, context=context
    )
    spans = await _spans(entry, aioclient_mock, hass)
    assert [attributes(span)["ha.type"] for span in spans] == ["state"]


async def _automation(hass: HomeAssistant, actions: list[dict[str, Any]]) -> None:
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "id": "example_motion_lights",
                "alias": "Example motion lights",
                "triggers": [{"trigger": "state", "entity_id": "binary_sensor.example_motion", "to": "on"}],
                "actions": actions,
            }
        },
    )


async def test_automation_run(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    _respond(hass)
    hass.states.async_set(LIGHT, "off")
    hass.states.async_set("binary_sensor.example_motion", "off")
    await _automation(hass, [{"action": "light.turn_on", "target": {"entity_id": LIGHT}}])
    hass.states.async_set("binary_sensor.example_motion", "on")

    spans = await _spans(entry, aioclient_mock, hass)
    [run] = _by_type(spans, "automation")
    [action] = _by_type(spans, "action")
    [response] = _by_type(spans, "response")
    assert run["name"] == "Example motion lights"
    assert "parentSpanId" not in run
    assert attributes(run)["ha.entity_id"] == "automation.example_motion_lights"
    assert attributes(run)["ha.automation_id"] == "example_motion_lights"
    assert "binary_sensor.example_motion" in attributes(run)["ha.trigger"]
    assert action["parentSpanId"] == run["spanId"]
    assert response["parentSpanId"] == action["spanId"]
    assert {span["traceId"] for span in (run, action, response)} == {run["traceId"]}

    [light_off] = [span for span in _by_type(spans, "state") if span["name"] == "light off"]
    assert attributes(light_off)["ha.cause"] == "automation"
    assert attributes(light_off)["ha.cause.name"] == "Example motion lights"


async def test_script_in_automation(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    _respond(hass)
    hass.states.async_set(LIGHT, "off")
    hass.states.async_set("binary_sensor.example_motion", "off")
    assert await async_setup_component(
        hass,
        "script",
        {
            "script": {
                "example_evening": {
                    "alias": "Example evening",
                    "sequence": [{"action": "light.turn_on", "target": {"entity_id": LIGHT}}],
                }
            }
        },
    )
    await _automation(hass, [{"action": "script.example_evening"}])
    hass.states.async_set("binary_sensor.example_motion", "on")

    spans = await _spans(entry, aioclient_mock, hass)
    [automation] = _by_type(spans, "automation")
    [script] = _by_type(spans, "script")
    calls = {span["name"]: span for span in _by_type(spans, "action")}
    assert calls["script.example_evening"]["parentSpanId"] == automation["spanId"]
    assert script["parentSpanId"] == calls["script.example_evening"]["spanId"]
    assert calls["light.turn_on"]["parentSpanId"] == script["spanId"]
    assert {span["traceId"] for span in spans if attributes(span)["ha.type"] != "state"} == {
        automation["traceId"]
    }
