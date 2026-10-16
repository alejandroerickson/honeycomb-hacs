"""State spans: how long each state lasted, and activity spans: how long a device was doing something.

okf/spec/01-telemetry.md, 1.1, 1.2 and 1.7. A span is sent when a state ends, so its duration is known
and nothing is held longer than one state.
"""

from __future__ import annotations

import math
from datetime import datetime

from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers import entity_registry as er

from .contexts import ContextTracer
from .describe import describe
from .filters import is_excluded
from .otlp import AttributeValue, Span
from .sender import SpanSender

# What a device is doing, where its state is only a setting: a thermostat set to heat is not always
# heating.
ACTIVITY = {"climate": "hvac_action", "humidifier": "action"}
READINGS = {
    "climate": ("current_temperature", "temperature", "current_humidity"),
    "humidifier": ("current_humidity", "humidity"),
}


class StateTracker:
    """Sends a span for every state, and every activity, that ends."""

    def __init__(self, hass: HomeAssistant, sender: SpanSender, contexts: ContextTracer) -> None:
        self._hass = hass
        self._sender = sender
        self._contexts = contexts
        # When each device's current activity began, from the first change seen.
        self._activity_since: dict[str, datetime] = {}

    @callback
    def async_start(self) -> CALLBACK_TYPE:
        """Start listening; return the function that stops it."""
        return self._hass.bus.async_listen(EVENT_STATE_CHANGED, self._state_changed)

    @callback
    def _state_changed(self, event: Event[EventStateChangedData]) -> None:
        old = event.data["old_state"]
        new = event.data["new_state"]
        # An entity appearing has no state that ended, and one disappearing has no next state.
        if old is None or new is None:
            return
        entry = er.async_get(self._hass).async_get(old.entity_id)
        if is_excluded(old, entry) or is_excluded(new, entry):
            return
        if old.state != new.state:
            self._sender.add(self.state_span(old, new, entry))
        if (attribute := ACTIVITY.get(old.domain)) and (
            span := self._activity_span(attribute, old, new, entry)
        ):
            self._sender.add(span)

    def state_span(self, old: State, new: State, entry: er.RegistryEntry | None) -> Span:
        """The span for a state that ended when `new` began."""
        attributes: dict[str, AttributeValue] = {
            **describe(self._hass, old, entry),
            "ha.type": "state",
            "ha.state": old.state,
            "ha.next_state": new.state,
        }
        if (value := _number(old.state)) is not None:
            attributes["ha.value"] = value
        # Caused by a person or an automation, rather than by the device itself.
        if new.context.user_id or new.context.parent_id:
            attributes["ha.context.id"] = new.context.id
        attributes.update(self._contexts.cause(new.context))
        return Span(f"{old.domain} {old.state}", old.last_changed, new.last_changed, attributes)

    def _activity_span(
        self, attribute: str, old: State, new: State, entry: er.RegistryEntry | None
    ) -> Span | None:
        """The span for an activity that ended, such as a furnace that stopped heating."""
        before, after = old.attributes.get(attribute), new.attributes.get(attribute)
        if before == after:
            return None
        since = self._activity_since.get(old.entity_id)
        self._activity_since[old.entity_id] = new.last_updated
        if since is None or before is None:
            return None
        attributes: dict[str, AttributeValue] = {
            **describe(self._hass, old, entry),
            "ha.type": "activity",
            "ha.state": old.state,
            "ha.activity": str(before),
            "ha.next_activity": str(after),
        }
        for reading in READINGS.get(old.domain, ()):
            if (value := _number(old.attributes.get(reading))) is not None:
                attributes[f"ha.{reading}"] = value
        attributes.update(self._contexts.cause(new.context))
        return Span(f"{old.domain} {before}", since, new.last_updated, attributes)


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)  # type: ignore[arg-type]
    except TypeError, ValueError:
        return None
    return number if math.isfinite(number) else None
