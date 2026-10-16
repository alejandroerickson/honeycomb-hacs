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
from .describe import describe, state_name
from .filters import Rules
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

    def __init__(
        self, hass: HomeAssistant, sender: SpanSender, contexts: ContextTracer, rules: Rules
    ) -> None:
        self._hass = hass
        self._sender = sender
        self._contexts = contexts
        self._rules = rules
        # What caused the change that began each entity's current state.
        self._began: dict[str, dict[str, AttributeValue]] = {}
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
            self._began.pop(event.data["entity_id"], None)
            return
        entry = er.async_get(self._hass).async_get(old.entity_id)
        if self._rules.excluded(self._hass, old, entry) or self._rules.excluded(self._hass, new, entry):
            return
        if old.state != new.state:
            began = self._began.pop(old.entity_id, None)
            if began is None:
                # The first change seen since start-up: what began the state is known only if its
                # context was followed.
                began = self._contexts.change_cause(old.entity_id, old.context, answered=False)
            ended = self._contexts.change_cause(new.entity_id, new.context)
            self._sender.add(self.state_span(old, new, entry, began, ended))
            self._began[new.entity_id] = ended
        if (attribute := ACTIVITY.get(old.domain)) and (
            span := self._activity_span(attribute, old, new, entry)
        ):
            self._sender.add(span)

    def state_span(
        self,
        old: State,
        new: State,
        entry: er.RegistryEntry | None,
        began: dict[str, AttributeValue],
        ended: dict[str, AttributeValue],
    ) -> Span:
        """The span for a state that ended when `new` began: what began it, and what ended it."""
        attributes: dict[str, AttributeValue] = {
            **describe(self._hass, old, entry),
            **self._rules.allowed_attributes(old),
            "ha.type": "state",
            "ha.state": old.state,
            "ha.next_state": new.state,
            **began,
            **_next(ended),
        }
        if (value := _number(old.state)) is not None:
            attributes["ha.value"] = value
        return Span(f"{old.domain} {state_name(old)}", old.last_changed, new.last_changed, attributes)

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
            **self._rules.allowed_attributes(old),
            "ha.type": "activity",
            "ha.state": old.state,
            "ha.activity": str(before),
            "ha.next_activity": str(after),
        }
        for reading in READINGS.get(old.domain, ()):
            if (value := _number(old.attributes.get(reading))) is not None:
                attributes[f"ha.{reading}"] = value
        attributes.update(_next(self._contexts.change_cause(new.entity_id, new.context)))
        return Span(f"{old.domain} {before}", since, new.last_updated, attributes)


def _next(cause: dict[str, AttributeValue]) -> dict[str, AttributeValue]:
    """A cause as what ended a span: `ha.cause` becomes `ha.next_cause`, and so on."""
    return {key.replace("ha.", "ha.next_", 1): value for key, value in cause.items()}


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)  # type: ignore[arg-type]
    except TypeError, ValueError:
        return None
    return number if math.isfinite(number) else None
