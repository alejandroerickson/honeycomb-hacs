---
type: Decision
title: Releases are GitHub releases, which HACS installs
description: A version is a tag with a GitHub release; main is not what users run.
tags: [decision, release, hacs]
generated: {by: agent:claude, at: 2026-10-14}
status: stable
---

# Releases are GitHub releases, which HACS installs

## Context

HACS offers a repository's GitHub releases to users, and falls back to the default branch only
when there are none. Users should run versions, not whatever is on `main`.

## Decision

- A version is a `v<semver>` tag with a GitHub release, and the same version in
  `manifest.json`.
- Published releases are never moved or deleted.

## Consequences

- `main` may hold unreleased work.

Specified in: [releasing](../operations/releasing.md).
