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
| State spans (1.1, 1.2), as traces of their own until context traces join them | Built, without `ha.attr.<name>` |
| Context traces: automation and script runs, service calls, people's actions (1.3) | Next |
| Health spans (1.4) | Planned |
| Default exclusions (1.5) | Built |
| Include/exclude rules and allowed attributes (`ha.attr.<name>`) in an options flow (1.5) | Planned, before the first release |
| A demonstration configuration with made-up entities, and Honeycomb queries and boards for it | Planned |
| An icon (`brand/` assets), then CI's HACS check without `ignore: brands` | Planned |
| Submission to the HACS default list | Later |

## Open questions

- How long to wait for a device's response before a service call is marked as having no effect;
  whether it should differ by domain (a cover takes longer than a light).
- Whether a state span should carry all of an entity's attributes by default, or none.
- How to send a burst after Home Assistant starts. Entities appearing send nothing, but many end a
  short `unavailable` or `unknown` state as their integrations connect.
- What to do about entities that change every few seconds (power, signal strength): each change is
  a span, which may be more than a home wants to send.
