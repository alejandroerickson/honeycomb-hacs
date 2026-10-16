---
type: Decision
title: Only Home Assistant's public interfaces
description: Events, states and registries, never another integration's internals, so it works on any installation and survives Home Assistant's releases.
tags: [decision, architecture, compatibility]
generated: {by: agent:claude, at: 2026-10-14}
status: stable
---

# Only Home Assistant's public interfaces

## Context

Home Assistant records each automation run step by step, with timings, but only in the trace
integration's internal data, which can change in any release. An integration that reads it works
until it doesn't, on every installation at once. The maintainer ruled this out on 2026-10-14.

## Decision

- Read only the event bus (`state_changed`, `call_service`, `automation_triggered`,
  `script_started`, the lifecycle events and `user_added`/`user_updated`), the state machine, the
  area, floor, device and entity registries, the config entries' states, and users' names.
  Resolve a service call's targets with Home Assistant's own target helper
  (`homeassistant.helpers.target`), so they match what the call acts on.
- Durations come from what those show: a state's `last_changed`, an automation's or script's
  `current` attribute falling back, a target's first state change after a service call.
- Never `hass.data` of another integration, or private modules of Home Assistant.

## Consequences

- Automation step names and condition results are not sent; a trace links to Home Assistant's
  own trace by `ha.automation_id`.
- Nothing to configure per home: every installation has the same events.

## Constrains

- A review rejects an import from `homeassistant.components.<other>` other than its constants.

Specified in: [what is sent](../spec/01-telemetry.md).
