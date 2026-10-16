---
type: System Concept
title: How the integration works, and where things are
description: The integration's parts, how an event becomes a span, and the repository map.
tags: [system, overview, repository-map]
generated: {by: agent:claude, at: 2026-10-14}
status: draft
---

# Overview

## In one paragraph

The integration is set up in Home Assistant's UI with a Honeycomb API key. It listens to Home
Assistant's event bus, turns events into spans as the [specification](../spec/01-telemetry.md)
says, and sends them to Honeycomb's OTLP endpoint over HTTP, batched, with the HTTP client Home
Assistant already has. Disabling the integration stops it.

## Parts

| File | Does |
|---|---|
| `custom_components/honeycomb/__init__.py` | Sets up a config entry: starts the sender and the listeners; sends what is queued on unload. |
| `custom_components/honeycomb/config_flow.py` | Asks for the key, region and service name; checks the key with `GET /1/auth`. The options flow holds what else to send or leave out. |
| `custom_components/honeycomb/states.py` | Makes a span of each state that ended, and of each thermostat or humidifier activity (1.1, 1.2, 1.7). |
| `custom_components/honeycomb/contexts.py` | Follows contexts: automation and script runs, people's actions, service calls and each device's response, as traces (1.3). |
| `custom_components/honeycomb/health.py` | Start-up time, stopping, and integrations that failed to set up (1.4). |
| `custom_components/honeycomb/describe.py` | What every span about an entity says: what, where, and which device; and how a span names a state. |
| `custom_components/honeycomb/filters.py` | What stays home by default, and the user's rules from the options (1.5). |
| `custom_components/honeycomb/sender.py` | The queue, batching and posting to `/v1/traces` (1.6). |
| `custom_components/honeycomb/otlp.py` | Spans, and their encoding as OTLP/JSON. |
| `custom_components/honeycomb/const.py` | The domain, the regions' API hosts, defaults. |
| `custom_components/honeycomb/strings.json`, `translations/en.json` | The UI's text. |
| `custom_components/honeycomb/brand/` | The icon (Honeycomb's mark), 256 and 512 px; Home Assistant shows it for the integration. |

## Repository map

| Path | What it is |
|---|---|
| `custom_components/honeycomb/` | The integration, as HACS installs it. |
| `tests/` | Tests on `pytest-homeassistant-custom-component`, which runs a real Home Assistant core. |
| `hacs.json` | HACS metadata: name, minimum Home Assistant version. |
| `scripts/` | `bootstrap.sh`, `check_publishable.py`. |
| `.githooks/`, `.github/` | The privacy hooks; CI, security workflow, Dependabot, gitleaks. |
| `okf/` | This bundle. |
| `.agents/skills/` | Agent skills; `.claude/skills` links to it. |
