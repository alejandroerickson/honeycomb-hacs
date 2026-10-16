---
type: Decision
title: Releases are GitHub releases, which HACS installs
description: A version is a tag with a GitHub release; main is not what users run. Users add the repository to HACS themselves; it is not on HACS's default list.
tags: [decision, release, hacs]
generated: {by: agent:claude, at: 2026-10-15}
status: stable
---

# Releases are GitHub releases, which HACS installs

## Context

HACS offers a repository's GitHub releases to users, and falls back to the default branch only
when there are none. Users should run versions, not whatever is on `main`.

HACS lists a repository in its own search only after a pull request to its default list is
reviewed; until then a user adds it as a custom repository. The maintainer chose on 2026-10-15 not
to submit it: a My Home Assistant link opens the repository in a user's HACS in one click.

## Decision

- A version is a `v<semver>` tag with a GitHub release, and the same version in
  `manifest.json`.
- Published releases are never moved or deleted.
- The integration is not submitted to HACS's default list. The README's My Home Assistant button
  (`my.home-assistant.io/redirect/hacs_repository/?owner=alejandroerickson&repository=honeycomb-hacs&category=integration`)
  adds it to a user's HACS as a custom repository.

## Consequences

- `main` may hold unreleased work.
- Nobody finds the integration by searching HACS; people come from the README, the button or a
  link to it.
- No review queue to wait in, and HACS's default-list rules do not apply beyond what CI already
  checks.

Specified in: [releasing](../operations/releasing.md).
