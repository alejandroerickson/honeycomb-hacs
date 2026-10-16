---
type: Roadmap
title: What is built, what is next, and the open questions
description: The status of each part of the specification, and the questions still open.
tags: [roadmap]
generated: {by: agent:claude, at: 2026-10-14}
status: draft
---

# Roadmap (2026-10-14)

## Status

| Part | Status |
|---|---|
| Config flow: API key, region, service name, checked against Honeycomb's `/1/auth` | Built |
| Repository: CI, hassfest and HACS validation, the privacy check and hooks | Built |
| OTLP/JSON sender with batching and a bounded queue (1.6) | Built |
| State spans (1.1, 1.2), with what caused them and the entity's device | Built, without `ha.attr.<name>` |
| Context traces: automation and script runs, people's actions, service calls and each device's response (1.3) | Built |
| Health spans: start-up time, stopping, integrations that failed (1.4) | Built |
| Activity spans: what a thermostat or humidifier was doing (1.7) | Built |
| Default exclusions (1.5) | Built |
| Include/exclude rules and allowed attributes (`ha.attr.<name>`) in an options flow (1.5) | Next |
| A demonstration configuration with made-up entities, and Honeycomb queries and boards for it | Planned |
| An icon: Honeycomb's mark in `brand/`, which Home Assistant and HACS's brands check read | Built |
| Submission to the HACS default list | Later |

## Open questions

- Whether the 60-second wait for a device's response should differ by domain: a cover or a cloud
  device takes longer than a light.
- Overlapping runs of a `parallel` automation are matched to their ends in the order they started,
  which is wrong when a later run finishes first. Public interfaces give nothing better yet.
- Whether a state span should carry all of an entity's attributes by default, or none.
- How to send a burst after Home Assistant starts. Entities appearing send nothing, but many end a
  short `unavailable` or `unknown` state as their integrations connect.
- What to do about entities that change every few seconds (power, signal strength): each change is
  a span, which may be more than a home wants to send.
