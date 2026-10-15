---
type: Decision
title: The integration runs inside Home Assistant and sends to Honeycomb directly
description: A HACS custom integration, not a bridge or a collector on another machine, so every kind of installation can use it.
tags: [decision, architecture, hacs]
generated: {by: agent:claude, at: 2026-10-14}
status: stable
---

# The integration runs inside Home Assistant and sends to Honeycomb directly

## Context

Telemetry could leave Home Assistant three ways: a bridge on another machine reading its
WebSocket API, an add-on or AppDaemon app on the same host, or an integration inside Home
Assistant. Not everyone has another machine, and add-ons exist only on Home Assistant OS and
Supervised installations. The maintainer chose the integration on 2026-10-14.

## Decision

- A custom integration, `custom_components/honeycomb`, distributed through HACS, configured in
  the UI, turned off by disabling it.
- It sends straight to Honeycomb's OTLP endpoint; no collector in between.

## Consequences

- Works on Home Assistant OS, Container, Core and Supervised alike, with nothing else to run.
- Its work shares Home Assistant's event loop: it must never block it, and must drop telemetry
  rather than slow the home ([delivery](../spec/01-telemetry.md)).
- The Honeycomb key lives in Home Assistant's config entry storage.

Specified in: [overview](../system/overview.md).
