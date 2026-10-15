"""State spans: how long each state lasted (okf/spec/01-telemetry.md, 1.1 and 1.2).

A span is sent when a state ends, so its duration is known and nothing is held longer than one
state.
"""

from __future__ import annotations

import math

from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    EVENT_STATE_CHANGED,
)
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
)

from .filters import is_excluded
from .otlp import AttributeValue, Span
from .sender import SpanSender


@callback
def async_track_states(hass: HomeAssistant, sender: SpanSender) -> CALLBACK_TYPE:
    """Send a span for every state that ends; return the function that stops it."""

    @callback
    def _state_changed(event: Event[EventStateChangedData]) -> None:
        old = event.data["old_state"]
        new = event.data["new_state"]
        # An entity appearing has no state that ended, one disappearing has no next state, and a
        # change of attributes alone does not end a state.
        if old is None or new is None or old.state == new.state:
            return
        entry = er.async_get(hass).async_get(old.entity_id)
        if is_excluded(old, entry) or is_excluded(new, entry):
            return
        sender.add(state_span(hass, old, new, entry))

    return hass.bus.async_listen(EVENT_STATE_CHANGED, _state_changed)


def state_span(hass: HomeAssistant, old: State, new: State, entry: er.RegistryEntry | None) -> Span:
    """The span for a state that ended when `new` began."""
    attributes: dict[str, AttributeValue | None] = {
        "ha.entity_id": old.entity_id,
        "ha.domain": old.domain,
        "ha.state": old.state,
        "ha.next_state": new.state,
        "ha.friendly_name": old.attributes.get(ATTR_FRIENDLY_NAME),
        "ha.device_class": old.attributes.get(ATTR_DEVICE_CLASS),
        "ha.unit": old.attributes.get(ATTR_UNIT_OF_MEASUREMENT),
        "ha.value": _number(old.state),
        **_area_and_floor(hass, entry),
    }
    # Caused by a person or an automation, rather than by the device itself.
    if new.context.user_id or new.context.parent_id:
        attributes["ha.context.id"] = new.context.id
    return Span(
        name=f"{old.domain} {old.state}",
        start=old.last_changed,
        end=new.last_changed,
        attributes={key: value for key, value in attributes.items() if value is not None},
    )


def _number(state: str) -> float | None:
    try:
        value = float(state)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _area_and_floor(hass: HomeAssistant, entry: er.RegistryEntry | None) -> dict[str, str]:
    """The entity's area, or else its device's, and the area's floor, by name."""
    if entry is None:
        return {}
    area_id = entry.area_id
    if area_id is None and entry.device_id and (device := dr.async_get(hass).async_get(entry.device_id)):
        area_id = device.area_id
    if area_id is None or (area := ar.async_get(hass).async_get_area(area_id)) is None:
        return {}
    names = {"ha.area": area.name}
    if area.floor_id and (floor := fr.async_get(hass).async_get_floor(area.floor_id)):
        names["ha.floor"] = floor.name
    return names
