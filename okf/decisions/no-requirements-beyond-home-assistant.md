---
type: Decision
title: No Python requirements beyond Home Assistant's own
description: Spans are sent as OTLP over HTTP in JSON with Home Assistant's aiohttp, not with the OpenTelemetry SDK.
tags: [decision, architecture, dependencies, otlp]
generated: {by: agent:claude, at: 2026-10-14}
status: stable
---

# No Python requirements beyond Home Assistant's own

## Context

The OpenTelemetry SDK and its OTLP exporter bring protobuf and their own pins, which can clash with
the versions Home Assistant and other integrations require, and every requirement is installed into
a user's Home Assistant. Honeycomb accepts OTLP over HTTP encoded as JSON (checked against its
`/v1/traces` endpoint on 2026-10-14).

## Decision

- `manifest.json` has no `requirements`.
- Spans are built as OTLP/JSON and posted with Home Assistant's shared `aiohttp` session.

## Consequences

- No dependency conflicts to chase on Home Assistant upgrades.
- The integration owns its batching, retries and span encoding: a small amount of code, tested
  here.

Specified in: [delivery](../spec/01-telemetry.md).
