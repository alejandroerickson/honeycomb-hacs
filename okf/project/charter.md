---
type: Charter
title: Honeycomb for Home Assistant, a home's events as traces
description: What the integration and this repository are for, and what they are not.
tags: [charter]
generated: {by: agent:claude, at: 2026-10-14}
status: stable
---

# Charter

## What it is

- **A Home Assistant integration, installed through HACS,** that sends what happens in a home to
  Honeycomb as traces: how long states lasted, what people did and how devices responded, and
  automation runs with what they caused ([what is sent](../spec/01-telemetry.md)).
- **Inside Home Assistant.** Nothing else to host: no bridge, no collector, no second machine
  ([decision](../decisions/the-integration-runs-inside-home-assistant.md)).
- **For any home, as it is.** It reads only Home Assistant's public interfaces and needs no list of
  entities, so it works on any installation and survives Home Assistant's releases
  ([decision](../decisions/only-public-home-assistant-interfaces.md)).
- **A public, MIT-licensed repository**, `alejandroerickson/honeycomb-hacs`, with the code, its
  specification and this bundle.

## What it is not

- Not a general OpenTelemetry exporter for every backend. It is shaped for Honeycomb's model of
  wide events and traces; other OTLP backends may work but are not the aim.
- Not a metrics pipeline. Long-term graphs of sensor values belong to Home Assistant's statistics,
  InfluxDB or Prometheus.
- Not a way to control the home. It only observes.
- Not a place for anyone's real home: examples, tests and screenshots are synthetic
  ([decision](../decisions/the-repository-is-public-and-okf-is-reference-only.md)).
