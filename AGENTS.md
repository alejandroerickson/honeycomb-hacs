# honeycomb-hacs: agent orientation

This file is for any agent working in this repository. `CLAUDE.md` is a symlink to it; keep one
copy.

## What this is

A [HACS](https://hacs.xyz/) custom integration for Home Assistant that sends what happens in a
home to [Honeycomb](https://www.honeycomb.io/) as traces: how long each state lasted, what people
did and what the devices did in response, and each automation run with what it caused. It runs
inside Home Assistant, reads only Home Assistant's public interfaces, and sends OTLP over HTTP
with the client Home Assistant already has. Start at `okf/index.md`.

| Path | What it is |
|---|---|
| `okf/` | **All documentation**: charter, decisions, the telemetry specification, the roadmap, how to work here. |
| `custom_components/honeycomb/` | The integration. |
| `tests/` | Tests, run against Home Assistant's own test harness. |
| `scripts/` | `bootstrap.sh` (set up a checkout) and `check_publishable.py` (the privacy check). |
| `.githooks/` | Hooks that run the privacy check on every commit and push. |
| `.agents/skills/` | Skills for agents. `.claude/skills` is a link to it. |

## This repository is public

`alejandroerickson/honeycomb-hacs` is public and MIT-licensed. Everything committed, every commit
message and every pull request's text is published, and history keeps it.

- **Nothing from a real home.** Examples, tests, fixtures and screenshots use made-up entities
  (`light.example_kitchen`, "Front Door"). No real names of people, rooms or devices, no
  addresses, network names, IP addresses, routines or health data. A screenshot is reviewed by the
  maintainer before it is committed.
- **No secrets.** The Honeycomb key lives in Home Assistant's config entry, or in `.env` for local
  experiments (ignored). Never in code, tests or docs.
- No session memory in the repository: no logs, handoff notes, records of requests, or to-do
  lists. Keep those in `_private/` (ignored) or in your own memory. Planned work belongs in
  `okf/spec/02-roadmap.md`.
- Commit messages and pull request descriptions describe the change, never the conversation.
- Never name private projects, clients, employers or files elsewhere on a machine.
- Tools that install their own instructions (memory, routing or workflow tools) keep them in your
  user-level configuration, never in this file, `.agents/skills/` or `okf/`.
- Stage files by name. `scripts/bootstrap.sh` turns on git hooks that refuse a commit or push
  carrying any of the above, including words on the maintainer's private deny list
  (`okf/operations/security-checks.md`). When one blocks, fix the content; never `--no-verify`.
- If you are unsure whether something may be published, leave it out and ask.

## Skills

| Skill | Use it |
|---|---|
| `okf-orient` | At the start of a task: what to read in `okf/`. |
| `okf-update` | Before finishing any change: which concepts it affects. |
| `okf-decision` | When a change makes, revises or reverses a durable choice. |
| `make-a-release` | When asked to release a version for HACS. |
| `audit-for-leaks` | When asked to check the repository or its history for secrets or private material. |

## Before you change anything

Read `okf/process/working-in-this-repository.md`. In short: only Home Assistant's public
interfaces ([decision](okf/decisions/only-public-home-assistant-interfaces.md)); no third-party
Python requirements ([decision](okf/decisions/no-requirements-beyond-home-assistant.md)); what a
home sends is the user's choice, with the sensitive kinds left out unless they opt in
([decision](okf/decisions/sensitive-data-stays-home-by-default.md)).

```sh
scripts/bootstrap.sh     # uv sync, and the git hooks
uv run pytest            # tests
uv run ruff check . && uv run ruff format --check .
```

## Git

- Start a session with `git pull --rebase --autostash`.
- Push to `main` directly; a ruleset blocks force-pushes and deletion of `main`, so never rewrite
  published history. Fix a mistake with a new commit.
- Commit only when the maintainer asks.
- Releases are tags with a GitHub release; HACS installs from them (`make-a-release`).

## Keep the documentation true

When a change makes something in `okf/` untrue, fix it in the same change (`okf-update`). A new
durable choice gets a record in `okf/decisions/` (`okf-decision`). Run
`python3 okf/tools/validate_okf.py` before committing; CI runs it too.
