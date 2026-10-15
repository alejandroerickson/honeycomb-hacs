---
type: Index
title: honeycomb-hacs knowledge bundle
description: The map of the documentation; start here.
tags: [index, okf]
generated: {by: agent:claude, at: 2026-10-14}
status: stable
okf_version: "0.2"
---

# honeycomb-hacs knowledge bundle

A Home Assistant integration, installed through HACS, that sends what happens in a home to
Honeycomb as traces.

## Map

- [Charter](project/charter.md): what the integration and the repository are, and are not.
- [Overview](system/overview.md): how the integration works, and where things are.
- [Decisions](decisions/index.md): the architectural decision records.
- [Specification](spec/index.md): [what is sent](spec/01-telemetry.md) and the
  [roadmap](spec/02-roadmap.md).
- [Local development](operations/local-development.md), [releasing](operations/releasing.md) and
  the [security checks](operations/security-checks.md).
- [Working in this repository](process/working-in-this-repository.md).
- [Ontology](ontology.md), [bundle guide](README.md), [tools](tools/index.md).

## Outside the bundle

- `README.md`: the introduction for people installing it.
- `AGENTS.md`: agent orientation (`CLAUDE.md` links to it).
- `SECURITY.md`: how to report a vulnerability.
- `.agents/skills/`: `okf-orient`, `okf-update`, `okf-decision`, `make-a-release`,
  `audit-for-leaks`.
