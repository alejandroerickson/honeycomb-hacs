---
type: Decision
title: The repository is public; okf/ holds reference knowledge only
description: Everything committed is published, so nothing from a real home, no secrets and no session memory go into the repository.
tags: [decision, okf, process, privacy, public]
generated: {by: agent:claude, at: 2026-10-14}
status: stable
---

# The repository is public; okf/ holds reference knowledge only

## Context

The repository is public and MIT-licensed from its first commit, and history goes wherever the
repository goes. It is built and demonstrated against real homes, and a home's configuration says
who lives there, what they own and when they are in.

## Decision

- `okf/` is the documentation. Outside it only `README.md`, `AGENTS.md` (`CLAUDE.md` links to
  it), `SECURITY.md` and `.agents/skills/`.
- Nothing from a real home: examples, tests and screenshots use made-up entities; a screenshot is
  reviewed by the maintainer before it is committed.
- No secrets, local paths, private network addresses or personal details. No logs, session notes,
  requests or to-do lists; planned work goes in the [roadmap](../spec/02-roadmap.md). Agents keep
  memory outside the repository.

## Consequences

- A check at commit, at push and in CI refuses what this rules out, and reads a private deny list
  that only the maintainer's checkout has ([security checks](../operations/security-checks.md)).

## Constrains

- `scripts/check_publishable.py` lists the places files may be; a new one is added there.

Specified in: [working in this repository](../process/working-in-this-repository.md).
