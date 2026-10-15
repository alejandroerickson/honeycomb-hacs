---
type: Process
title: How to change this repository
description: The rules every change follows, for people and agents, including what may never be committed.
tags: [process, agents, contributing, public]
generated: {by: agent:claude, at: 2026-10-14}
status: stable
---

# Working in this repository

## The repository is public

Everything committed, including history, commit messages and pull requests' text, is published
([decision](../decisions/the-repository-is-public-and-okf-is-reference-only.md)).

- Nothing from a real home: examples, tests, fixtures and screenshots use made-up entities. A
  screenshot is reviewed by the maintainer before it is committed, and kept under `okf/media/`.
- No secrets, tokens, absolute local paths, private network addresses or personal details. No
  names of private projects, clients or employers.
- No session notes, logs, requests or to-do lists. They go in `_private/` (ignored). Planned work
  goes in the [roadmap](../spec/02-roadmap.md).
- Commit messages and pull request descriptions describe the change, never the conversation.
- `scripts/bootstrap.sh` turns on git hooks that refuse a commit or push carrying any of this, and
  CI checks again ([security checks](../operations/security-checks.md)). When a hook blocks, fix
  the content; never `--no-verify`.

## Changing behavior

1. **Public interfaces only.** Read events, states and registries; never `hass.data` of another
   integration or anything private in Home Assistant
   ([decision](../decisions/only-public-home-assistant-interfaces.md)).
2. **No new requirements** in `manifest.json`
   ([decision](../decisions/no-requirements-beyond-home-assistant.md)).
3. **Specify, then build.** A change to what is sent changes
   [the telemetry specification](../spec/01-telemetry.md) in the same commit.
4. **Privacy defaults** only get stricter without a decision
   ([decision](../decisions/sensitive-data-stays-home-by-default.md)).
5. **Tests** use the Home Assistant test harness and made-up entities; nothing reaches Honeycomb in
   a test.

## Before you finish

- `uv run pytest`, `uv run ruff check .` and `uv run ruff format --check .` pass.
- A change a user would notice bumps `version` in `manifest.json` at release time
  ([releasing](../operations/releasing.md)).
- Update the bundle, and run `python3 okf/tools/validate_okf.py`.
