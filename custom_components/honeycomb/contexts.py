"""Context traces: what automations, scripts and people did, and how the home responded.

okf/spec/01-telemetry.md, 1.3. An automation or script run, or a person's action, is a trace. Each
service call in it is a span that lasts until every entity it targets has responded, with a response
span for each entity: how long the device took, or that it never did.
"""

from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from homeassistant.const import (
    ATTR_DOMAIN,
    ATTR_ENTITY_ID,
    ATTR_NAME,
    ATTR_SERVICE,
    ATTR_SERVICE_DATA,
    EVENT_CALL_SERVICE,
    EVENT_STATE_CHANGED,
    STATE_UNAVAILABLE,
)
from homeassistant.core import CALLBACK_TYPE, Context, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.target import TargetSelection, async_extract_referenced_entity_ids

from .describe import describe, state_name
from .filters import Rules
from .otlp import AttributeValue, Span
from .sender import SpanSender

# Public event names, from the automation and script integrations.
EVENT_AUTOMATION_TRIGGERED = "automation_triggered"
EVENT_SCRIPT_STARTED = "script_started"
EVENT_USER_ADDED = "user_added"
EVENT_USER_UPDATED = "user_updated"
ATTR_SOURCE = "source"
ATTR_CURRENT = "current"

RESPONSE_TIMEOUT = timedelta(seconds=60)
RUN_TIMEOUT = timedelta(hours=2)
CHECK_INTERVAL = timedelta(seconds=5)
MAX_CONTEXTS = 2000

# The state a service asks for: an entity already there has nothing to do.
REQUESTED = {
    "turn_on": ("on",),
    "turn_off": ("off",),
    "open_cover": ("open", "opening"),
    "close_cover": ("closed", "closing"),
    "lock": ("locked", "locking"),
    "unlock": ("unlocked", "unlocking"),
}
# Script services that are not the name of a script.
SCRIPT_SERVICES = {"turn_on", "turn_off", "toggle", "reload"}


@dataclass(eq=False)
class _Trace:
    trace_id: str
    root_span_id: str
    cause: dict[str, str]


@dataclass(eq=False)
class _Run:
    span: Span
    entity_id: str
    context_id: str


@dataclass(eq=False)
class _Call:
    span: Span
    context_id: str
    deadline: datetime
    cause: dict[str, str]
    pending: set[str] = field(default_factory=set)
    counts: dict[str, int] = field(default_factory=dict)

    def count(self, effect: str, number: int = 1) -> None:
        self.counts[effect] = self.counts.get(effect, 0) + number


class ContextTracer:
    """Follows contexts from the event bus and turns them into traces."""

    def __init__(self, hass: HomeAssistant, sender: SpanSender, rules: Rules) -> None:
        self._hass = hass
        self._sender = sender
        self._rules = rules
        self._traces: OrderedDict[str, _Trace] = OrderedDict()
        self._runs_by_entity: dict[str, deque[_Run]] = {}
        self._runs_by_context: dict[str, list[_Run]] = {}
        self._calls: list[_Call] = []
        self._calls_by_target: dict[str, _Call] = {}
        # The call each entity's last change answered, by the context of that change.
        self._answered: dict[str, tuple[str, _Call]] = {}
        self._users: dict[str, str] = {}

    async def async_start(self) -> list[CALLBACK_TYPE]:
        """Start following; return the functions that stop it."""
        await self._async_load_users()
        bus = self._hass.bus
        return [
            bus.async_listen(EVENT_AUTOMATION_TRIGGERED, self._run_started),
            bus.async_listen(EVENT_SCRIPT_STARTED, self._run_started),
            bus.async_listen(EVENT_CALL_SERVICE, self._service_called),
            bus.async_listen(EVENT_STATE_CHANGED, self._state_changed),
            bus.async_listen(EVENT_USER_ADDED, self._users_changed),
            bus.async_listen(EVENT_USER_UPDATED, self._users_changed),
            async_track_time_interval(self._hass, self._check_timeouts, CHECK_INTERVAL),
        ]

    async def _async_load_users(self) -> None:
        self._users = {user.id: user.name for user in await self._hass.auth.async_get_users() if user.name}

    @callback
    def _users_changed(self, _event: Event) -> None:
        self._hass.async_create_task(self._async_load_users(), eager_start=False)

    def change_cause(
        self, entity_id: str, context: Context, *, answered: bool = True
    ) -> dict[str, AttributeValue]:
        """Who or what caused a change to an entity in this context, with the context's id.

        A device that responds more than five seconds after a call gets a new context from Home
        Assistant; its change is still the call's doing. With `answered`, a change to an entity a
        call is waiting on, or that answered one, is credited to that call.
        """
        if trace := self._traces.get(context.id):
            return {**trace.cause, "ha.context.id": context.id}
        if answered:
            call = self._calls_by_target.get(entity_id)
            if call is None and (last := self._answered.get(entity_id)) and last[0] == context.id:
                call = last[1]
            if call is not None:
                return {**call.cause, "ha.context.id": call.context_id}
        # Caused by a person or an automation the integration did not follow.
        if context.user_id or context.parent_id:
            return {"ha.context.id": context.id}
        return {}

    # ---- Runs: automations and scripts ---------------------------------------------------------

    @callback
    def _run_started(self, event: Event) -> None:
        context = event.context
        entity_id = event.data.get(ATTR_ENTITY_ID)
        if not entity_id:
            return
        name = event.data.get(ATTR_NAME) or entity_id
        kind = "automation" if event.event_type == EVENT_AUTOMATION_TRIGGERED else "script"
        attributes: dict[str, AttributeValue] = {
            "ha.type": kind,
            "ha.entity_id": entity_id,
            "ha.context.id": context.id,
        }
        if source := event.data.get(ATTR_SOURCE):
            attributes["ha.trigger"] = str(source)
        if (entry := er.async_get(self._hass).async_get(entity_id)) and entry.unique_id:
            attributes[f"ha.{kind}_id"] = entry.unique_id
        start = event.time_fired

        # A script runs in the context of what started it; an automation in a new context whose
        # parent is the change that triggered it.
        trace = self._traces.get(context.id) or (
            self._traces.get(context.parent_id) if context.parent_id else None
        )
        span = Span(name, start, start, attributes)
        cause = {"ha.cause": kind, "ha.cause.name": name}
        if trace is None:
            trace = _Trace(span.trace_id, span.span_id, cause)
        else:
            span.trace_id = trace.trace_id
            span.parent_span_id = self._parent_span_id(trace, context.id, context.parent_id, target=entity_id)
        if context.id not in self._traces:
            self._remember(context.id, _Trace(trace.trace_id, trace.root_span_id, cause))
        run = _Run(span, entity_id, context.id)
        self._runs_by_entity.setdefault(entity_id, deque()).append(run)
        self._runs_by_context.setdefault(context.id, []).append(run)

    def _end_runs(self, entity_id: str, count: int, end: datetime) -> None:
        runs = self._runs_by_entity.get(entity_id)
        for _ in range(count):
            if not runs:
                return
            self._end_run(runs.popleft(), end)

    def _end_run(self, run: _Run, end: datetime, *, timed_out: bool = False) -> None:
        if (in_context := self._runs_by_context.get(run.context_id)) and run in in_context:
            in_context.remove(run)
            if not in_context:
                del self._runs_by_context[run.context_id]
        run.span.end = max(end, run.span.start)
        if timed_out:
            run.span.attributes["ha.timed_out"] = True
        self._sender.add(run.span)

    def _parent_span_id(self, trace: _Trace, *context_ids: str | None, target: str | None = None) -> str:
        """The innermost open span to hang a new one under."""
        if target and (call := self._calls_by_target.get(target)) and call.span.trace_id == trace.trace_id:
            return call.span.span_id
        for context_id in context_ids:
            if context_id and (runs := self._runs_by_context.get(context_id)):
                return runs[-1].span.span_id
        return trace.root_span_id

    def _remember(self, context_id: str, trace: _Trace) -> None:
        self._traces[context_id] = trace
        self._traces.move_to_end(context_id)
        while len(self._traces) > MAX_CONTEXTS:
            self._traces.popitem(last=False)

    # ---- Service calls and responses -----------------------------------------------------------

    @callback
    def _service_called(self, event: Event) -> None:
        context = event.context
        domain = event.data.get(ATTR_DOMAIN)
        service = event.data.get(ATTR_SERVICE)
        if not domain or not service:
            return
        trace = self._traces.get(context.id)
        person = trace is None and context.user_id is not None and context.parent_id is None
        if trace is None and not person:
            return  # Not caused by a person, or by a run that was followed.
        targets = self._targets(domain, service, event.data.get(ATTR_SERVICE_DATA) or {})
        if targets is None:
            return  # Every target is left out by default.

        start = event.time_fired
        attributes: dict[str, AttributeValue] = {
            "ha.type": "action",
            "ha.service": f"{domain}.{service}",
            "ha.domain": domain,
            "ha.context.id": context.id,
            "ha.targets": len(targets),
        }
        span = Span(f"{domain}.{service}", start, start, attributes)
        if trace is None:
            cause: dict[str, str] = {"ha.cause": "person"}
            if user := self._users.get(context.user_id or ""):
                span.attributes["ha.user"] = cause["ha.user"] = user
            self._remember(context.id, _Trace(span.trace_id, span.span_id, cause))
        else:
            cause = trace.cause
            span.trace_id = trace.trace_id
            span.parent_span_id = self._parent_span_id(trace, context.id)

        call = _Call(span, context.id, start + RESPONSE_TIMEOUT, dict(cause))
        requested = REQUESTED.get(service)
        for entity_id in targets:
            state = self._hass.states.get(entity_id)
            # Events fired while another is handled are queued, so a device may have changed in this
            # call's context before the call reaches us; its change is still to come.
            responded = state is not None and state.context.id == context.id
            if not responded and (state is None or state.state == STATE_UNAVAILABLE):
                call.count("unavailable")
            elif not responded and requested and state.state in requested:
                call.count("already")
            else:
                if previous := self._calls_by_target.get(entity_id):
                    # Not answered before a newer call: the older call's wait for it ends here.
                    previous.pending.discard(entity_id)
                    previous.count("superseded")
                    self._sender.add(self._unanswered_span(previous, entity_id, "superseded", start))
                    if not previous.pending:
                        self._finish_call(previous, start)
                call.pending.add(entity_id)
                self._calls_by_target[entity_id] = call
        if call.pending:
            self._calls.append(call)
        else:
            self._finish_call(call, start)

    def _targets(self, domain: str, service: str, data: dict) -> set[str] | None:
        """The entities a call is meant to change; None if every one of them stays home."""
        if domain == "script" and service not in SCRIPT_SERVICES:
            entity_ids = {f"script.{service}"}
        else:
            selected = async_extract_referenced_entity_ids(self._hass, TargetSelection(data))
            entity_ids = selected.referenced | selected.indirectly_referenced
            if domain != "homeassistant":
                entity_ids = {entity_id for entity_id in entity_ids if entity_id.split(".", 1)[0] == domain}
        entities = er.async_get(self._hass)
        kept = {
            entity_id
            for entity_id in entity_ids
            if (state := self._hass.states.get(entity_id)) is None
            or not self._rules.excluded(self._hass, state, entities.async_get(entity_id))
        }
        return None if entity_ids and not kept else kept

    @callback
    def _state_changed(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        old, new = event.data["old_state"], event.data["new_state"]
        if old is not None and new is not None and entity_id.startswith(("automation.", "script.")):
            before = old.attributes.get(ATTR_CURRENT) or 0
            after = new.attributes.get(ATTR_CURRENT) or 0
            if after < before:
                self._end_runs(entity_id, before - after, new.last_updated)
        call = self._calls_by_target.pop(entity_id, None)
        if call is None or new is None:
            return
        self._answered[entity_id] = (new.context.id, call)
        call.pending.discard(entity_id)
        call.count("changed")
        attributes: dict[str, AttributeValue] = {
            **describe(self._hass, new, er.async_get(self._hass).async_get(entity_id)),
            **self._rules.allowed_attributes(new),
            "ha.type": "response",
            "ha.state": new.state,
            "ha.effect": "changed",
            "ha.context.id": call.context_id,
            "ha.same_context": new.context.id == call.context_id,
        }
        if old is not None:
            attributes["ha.previous_state"] = old.state
        end = new.last_updated
        self._sender.add(
            Span(
                f"{new.domain} → {state_name(new)}",
                call.span.start,
                max(end, call.span.start),
                attributes,
                trace_id=call.span.trace_id,
                parent_span_id=call.span.span_id,
            )
        )
        if not call.pending:
            self._finish_call(call, end)

    @callback
    def _check_timeouts(self, now: datetime) -> None:
        for call in [call for call in self._calls if now >= call.deadline]:
            for entity_id in sorted(call.pending):
                self._calls_by_target.pop(entity_id, None)
                self._sender.add(self._unanswered_span(call, entity_id, "none", call.deadline))
            call.count("none", len(call.pending))
            call.pending.clear()
            self._finish_call(call, call.deadline)
        cutoff = now - RUN_TIMEOUT
        for runs in list(self._runs_by_entity.values()):
            while runs and runs[0].span.start < cutoff:
                self._end_run(runs.popleft(), now, timed_out=True)

    def _unanswered_span(self, call: _Call, entity_id: str, effect: str, end: datetime) -> Span:
        """A target that did not respond to a call: before the timeout (`none`), or before a newer call."""
        attributes: dict[str, AttributeValue] = {"ha.entity_id": entity_id}
        if state := self._hass.states.get(entity_id):
            attributes = describe(self._hass, state, er.async_get(self._hass).async_get(entity_id))
        attributes.update({"ha.type": "response", "ha.effect": effect, "ha.context.id": call.context_id})
        label = "no effect" if effect == "none" else effect
        return Span(
            f"{entity_id.split('.', 1)[0]} → {label}",
            call.span.start,
            max(end, call.span.start),
            attributes,
            trace_id=call.span.trace_id,
            parent_span_id=call.span.span_id,
        )

    def _finish_call(self, call: _Call, end: datetime) -> None:
        if call in self._calls:
            self._calls.remove(call)
        counts = call.counts
        if counts.get("none"):
            effect = "partial" if counts.get("changed") else "none"
        elif counts.get("changed"):
            effect = "changed"
        elif counts.get("already"):
            effect = "already"
        elif counts.get("unavailable"):
            effect = "unavailable"
        else:
            effect = None
        if effect:
            call.span.attributes["ha.effect"] = effect
        for name, number in counts.items():
            call.span.attributes[f"ha.{name}"] = number
        call.span.end = max(end, call.span.start)
        self._sender.add(call.span)
