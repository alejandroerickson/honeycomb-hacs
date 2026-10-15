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

Everything comes from Home Assistant's public interfaces: the event bus, the state machine and the
area, device and entity registries
([decision](../decisions/only-public-home-assistant-interfaces.md)). Spans go to Honeycomb as OTLP
over HTTP, encoded as JSON, with the integration's service name as `service.name` and the
instrumentation scope `honeycomb-hacs` at the integration's version
([decision](../decisions/no-requirements-beyond-home-assistant.md)).

## 1.1 State spans: how long each state lasted

When an entity's state changes, the integration MUST send one span covering the state that just
ended: from its `last_changed` to the new state's `last_changed`. The span is named
`<domain> <old state>` (`light on`, `binary_sensor on`, `climate heat`).

Only a change of state ends one. An entity appearing, an entity being removed and a change of
attributes alone send nothing.

Attributes: `ha.entity_id`, `ha.domain`, `ha.state` (the state that ended), `ha.next_state`,
`ha.area`, `ha.floor`, `ha.device_class`, `ha.unit`, `ha.friendly_name`, and for a state that
reads as a finite number `ha.value` as a float. `ha.area` is the entity's area, or else its
device's, and `ha.floor` that area's floor, both by name. An attribute with no value is left off.
Attributes the user allows are added as `ha.attr.<name>`.

A span whose state ended in a change caused by a context (one with a user or a parent: a person, an
automation) carries `ha.context.id` and joins that context's trace (1.3). Otherwise it is a trace
of its own.

◆ Decision: a span describes a state that *ended*, so its duration is known when it is sent and
nothing is held in memory longer than one state.

## 1.2 Unavailable

A state of `unavailable` or `unknown` is a state span like any other (`ha.state: unavailable`),
so how long devices are away is a duration query.

## 1.3 Contexts: what people and automations caused

Home Assistant gives every action a context; the service calls and state changes it causes carry
its id, and the contexts they create carry it as `parent_id`. The integration MUST map a context to
a trace, and its parent to the parent trace.

- **An automation or script run** is a root span from its `automation_triggered` or
  `script_started` event to the moment the entity's `current` attribute falls back. Its trigger's
  description is `ha.trigger`.
- **A service call** (`call_service`) is a child span that ends when the first entity it targets
  changes state in the same context: how long the device took. If none changes within a timeout
  (the default is 60 seconds), the span ends at the timeout with `ha.effect: none`.
- **A person's action** (a context with a `user_id` and no parent) is a root span named after
  the service call, with `ha.user` as the user's name, never their id.

Delays and waits inside an automation appear as the gaps between its children. Step names and
condition results are not available through public interfaces and are not sent; `ha.automation_id`
lets a reader open Home Assistant's own trace.

## 1.4 Home Assistant's health

`homeassistant_start`, `homeassistant_stop` and a config entry failing to set up are sent as
spans with `ha.event`.

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

Users choose more with include and exclude rules by domain, entity id pattern, area or device
class ([decision](../decisions/sensitive-data-stays-home-by-default.md)).

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
