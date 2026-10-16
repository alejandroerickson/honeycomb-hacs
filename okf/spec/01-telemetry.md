---
type: Specification
title: What the integration sends to Honeycomb
description: Which Home Assistant events become spans, how they are linked into traces, their attributes, and what is left out.
tags: [spec, telemetry, traces, privacy]
generated: {by: agent:claude, at: 2026-10-14}
status: draft
---

# What is sent

Draft: this is the design being built. The [roadmap](02-roadmap.md) says what exists.

Everything comes from Home Assistant's public interfaces: the event bus, the state machine, the
area, floor, device and entity registries, and its users' names
([decision](../decisions/only-public-home-assistant-interfaces.md)). Spans go to Honeycomb as OTLP
over HTTP, encoded as JSON, with the integration's service name as `service.name` and the
instrumentation scope `honeycomb-hacs` at the integration's version
([decision](../decisions/no-requirements-beyond-home-assistant.md)).

Every span has `ha.type`, saying which kind it is: `state` (1.1, 1.2), `automation`, `script`,
`action` or `response` (1.3), `health` (1.4) or `activity` (1.7).

## 1.1 State spans: how long each state lasted

When an entity's state changes, the integration MUST send one span covering the state that just
ended: from its `last_changed` to the new state's `last_changed`. The span is named
`<domain> <old state>` (`light on`, `binary_sensor on`, `climate heat`), except where the state is a
free value: for `sensor`, `number`, `input_number`, `counter`, `input_text`, `text`,
`input_datetime`, `date`, `datetime`, `time` and `event`, the name gives the device class instead
(`sensor power`), or `value` when there is none, so that names stay few. An `enum` sensor, and any
entity `unavailable` or `unknown`, keeps its state in the name.

Only a change of state ends one. An entity appearing, an entity being removed and a change of
attributes alone send nothing.

Attributes: `ha.state` (the state that ended), `ha.next_state`, for a state that reads as a finite
number `ha.value` as a float, and what every span about an entity says about it:

- `ha.entity_id`, `ha.domain`, `ha.friendly_name`, `ha.device_class`, `ha.unit`;
- `ha.area`, the entity's area or else its device's, and `ha.floor`, that area's floor, both by
  name;
- `ha.integration` (the integration that provides the entity), and its device's `ha.device`
  (name), `ha.device.manufacturer` and `ha.device.model`.

An attribute with no value is left off. Attributes the user allows are added as `ha.attr.<name>`.

A span says what began its state and what ended it, when a context did (one with a user or a
parent: a person, an automation). For the change that began the state: `ha.context.id`, and when
that context belongs to a trace the integration followed (1.3), `ha.cause` (`automation`, `script`
or `person`) with `ha.cause.name` (the automation's or script's name) or `ha.user`. For the change
that ended it, the same with `next`: `ha.next_context.id`, `ha.next_cause`, `ha.next_cause.name`,
`ha.next_user`. A change that answered a call is the call's doing, even when the device was too
slow to keep the call's context (1.3). What began the first state seen after start-up is known only
if its context was followed. The span stays a trace of its own, since the state began long before
the trace did; the trace has a response span for the change.

◆ Decision: a span describes a state that *ended*, so its duration is known when it is sent and
nothing is held in memory longer than one state.

## 1.2 Unavailable

A state of `unavailable` or `unknown` is a state span like any other (`ha.state: unavailable`),
so how long devices are away is a duration query.

## 1.3 Contexts: what people and automations caused

Home Assistant gives every action a context; the service calls and state changes it causes carry
its id, and the contexts they create carry it as `parent_id`. The integration MUST map a context to
a trace, and its parent to the parent trace.

- **An automation or script run** is a span named after the automation or script, from its
  `automation_triggered` or `script_started` event to the moment the entity's `current` attribute
  falls back. Attributes: `ha.type` (`automation` or `script`), `ha.entity_id`, `ha.automation_id`
  or `ha.script_id`, `ha.trigger` (the trigger's description) and `ha.context.id`. A run is the
  root of its trace, unless what started it belongs to a trace already: a script called by an
  automation hangs under that call, and an automation triggered by a change another run made joins
  that run's trace. Overlapping runs of one automation are matched to their ends in the order they
  started. A run still open after two hours is sent with `ha.timed_out: true`.
- **A person's action** (a service call in a context with a `user_id` and no parent) is the root
  span of its trace, with `ha.user` as the user's name, never their id.
- **A service call** (`call_service`) is a span named `<domain>.<service>` (`light.turn_on`) under
  the run that made it. Its targets are the entities it names, or that its devices, areas, floors
  and labels hold, in the service's domain; `ha.targets` is how many. It lasts until every target
  has responded, or until the timeout (60 seconds). `ha.effect` sums it up: `changed` (every
  target responded), `partial`, `none` (none did), `already` (every target was already in the
  requested state) or `unavailable`; `ha.changed`, `ha.none`, `ha.already`, `ha.unavailable` and
  `ha.superseded` count the targets. The call's data is never sent. A call neither by a person nor
  inside a run the integration followed is not sent, and nor is one whose targets are all left out
  (1.5).
- **A response** is a span under the call, from the call to the target's first change after it:
  how long the device took. It is named `<domain> → <new state>` (`light → on`) and carries the
  entity's attributes (1.1), `ha.state`, `ha.previous_state`, `ha.effect: changed` and
  `ha.same_context`, whether the change carried the call's context (a device that reports more
  than five seconds later gets a new one; its change still answers the call). A free value is named
  as in 1.1. A target that does not change before the timeout gets a span named
  `<domain> → no effect` with `ha.effect: none`, ending at the timeout. A target already in the
  requested state (`turn_on`, `turn_off`, opening, closing, locking, unlocking) or unavailable gets
  no response span. When a newer call targets an entity before it has responded, the change answers
  the newer call, and the older call gets a span named `<domain> → superseded` with
  `ha.effect: superseded`, ending when the newer call was made, so a command that was never carried
  out is not hidden by the one that followed it.

Delays and waits inside an automation appear as the gaps between its children. Step names and
condition results are not available through public interfaces and are not sent; `ha.automation_id`
lets a reader open Home Assistant's own trace.

## 1.4 Home Assistant's health

Health spans have `ha.type: health` and `ha.version`, Home Assistant's version.

- **`homeassistant start`**: from `homeassistant_start` to `homeassistant_started`, how long
  Home Assistant took to start. Sent only when the integration is set up as Home Assistant starts,
  not when it is added to one already running.
- **`<domain> <state>`** for each config entry that failed to set up by then (`setup_error`,
  `setup_retry`, `migration_error`), with `ha.integration` and `ha.entry_state`. Never the entry's
  title or the reason it failed, which can hold names and network addresses.
- **`homeassistant stop`** when Home Assistant stops.

## 1.5 What is left out

The integration MUST NOT send, unless the user includes them by name:

- the domains `device_tracker`, `person` and `zone`, and any attribute holding a latitude,
  longitude or GPS accuracy;
- entities of the companion app (the `mobile_app` platform): a phone's sensors report where its
  owner is, their activity, sleep, steps, networks and notifications;
- sensors whose device class or unit describe a body (heart rate, blood pressure, sleep, steps,
  body temperature and the like);
- `camera` and `image` entities, media titles, and any attribute named `entity_picture`,
  `access_token` or `token`.

Home Assistant has no device class for most body measurements, so a `sensor` or `binary_sensor` is
taken to describe a body when its unit is one only a body has (`bpm`, `beats/min`, `breaths/min`,
`steps`, `mg/dL`, `mmol/L`) or its entity id has a body measurement as a word (`heart_rate`,
`hrv`, `blood_pressure`, `systolic`, `glucose`, `spo2`, `respiratory_rate`, `body_fat`, `weight`,
`sleep`, `asleep`, `steps`, `vo2max` and the like; the list is in `filters.py`). An entity is left
out when either the state that ended or the next one matches.

Users choose more in the integration's options
([decision](../decisions/sensitive-data-stays-home-by-default.md)); saving them reloads the
integration:

- **Leave out**: entity id patterns, where `*` stands for any text (`sensor.*_power`; `sensor.*`
  for a whole domain), areas (an entity's own, or else its device's) and device classes.
- **Send anyway**: entity id patterns for what is left out by default. What the user leaves out
  stays out even when it is also included.
- **Attributes**: attribute names, sent as `ha.attr.<name>` on every span about an entity that has
  them. A number, text or true/false is sent as it is; anything else as JSON. Naming a location or
  token attribute here is including it by name.

## 1.6 Delivery

Spans are batched and sent at least every 10 seconds, at once when 1,000 are waiting, and when Home
Assistant stops or the integration is unloaded. A request carries at most 1,000 spans. Home
Assistant never waits on Honeycomb: queueing a span is all an event listener does.

- **Honeycomb unreachable** (a connection error, a timeout after 10 seconds, HTTP 408, 429 or 5xx):
  the batch goes back to the front of the queue for the next attempt. One warning is logged, and
  one note when sending works again.
- **A batch refused** (any other HTTP 4xx): it is dropped and the error logged, since sending it
  again would fail the same way.
- **The queue is full** (10,000 spans): the oldest are dropped first. One warning is logged, then
  how many were dropped once a batch is sent.

## 1.7 Activity spans: what a device was doing

Some devices' state is a setting, not what they are doing: a thermostat set to `heat` is not always
heating. For these, the integration MUST also send a span covering each activity that ended, as it
does for states: `hvac_action` for `climate` and `action` for `humidifier`. The span is named
`<domain> <activity>` (`climate heating`).

Attributes: the entity's (1.1), `ha.state` (the setting), `ha.activity`, `ha.next_activity`, and the
readings when the activity ended: `ha.current_temperature`, `ha.temperature` (the target),
`ha.current_humidity`, `ha.humidity`. The first change after start-up starts the clock, since when
the activity before it began is not known.
