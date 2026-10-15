---
type: Process
title: Developing locally
description: Setting up a checkout, running the tests and checks, and trying the integration against Honeycomb.
tags: [operations, development, ci]
generated: {by: agent:claude, at: 2026-10-14}
status: stable
---

# Local development

Needs Python 3.14 (Home Assistant's), [uv](https://docs.astral.sh/uv/) and
[gitleaks](https://github.com/gitleaks/gitleaks).

```sh
scripts/bootstrap.sh                                  # uv sync; turns on the git hooks
uv run pytest                                         # tests, on a real Home Assistant core
uv run ruff check . && uv run ruff format --check .   # lint and format
python3 okf/tools/validate_okf.py                     # the bundle
```

The test harness, `pytest-homeassistant-custom-component`, is pinned in `pyproject.toml` to one
Home Assistant release; Dependabot moves it.

## Trying it against Honeycomb

Put a Honeycomb key in `.env` (ignored) as `HONEYCOMB_API_KEY`. Use a Honeycomb environment
kept for experiments, so test data never mixes with a real home's.

## CI

`.github/workflows/ci.yml` runs on each pull request and push to `main`: the bundle validator,
lint, the tests, Home Assistant's `hassfest`, the HACS validation, and the
[privacy check](security-checks.md). Actions are pinned to commits; Dependabot updates them.
