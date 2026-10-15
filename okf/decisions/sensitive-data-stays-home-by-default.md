---
type: Decision
title: Sensitive data stays home unless the user includes it
description: Locations, body measurements, cameras and tokens are excluded by default; everything else is the user's choice.
tags: [decision, privacy]
generated: {by: agent:claude, at: 2026-10-14}
status: stable
---

# Sensitive data stays home unless the user includes it

## Context

Sending everything by default is what makes the integration work for any home with no setup. But
a home's events include where people are and readings from their bodies, and they would go to a
third party.

## Decision

- Excluded by default: `device_tracker`, `person`, `zone`, location attributes, the companion
  app's phone sensors, body measurements, cameras and images, media titles, and token-like
  attributes ([the list](../spec/01-telemetry.md)).
- A user includes any of them only by naming it.
- People appear by their Home Assistant user's name, never their user id.

## Consequences

- A default exclusion is removed only by a new decision; adding one needs none.

Specified in: [what is left out](../spec/01-telemetry.md).
