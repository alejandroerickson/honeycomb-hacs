---
type: Bundle Guide
title: How to read and keep this documentation bundle
description: What okf/ is, how it is laid out, the reading order, and how to keep it accurate.
tags: [guide, okf]
generated: {by: agent:claude, at: 2026-10-14}
status: stable
---

# The OKF bundle

An [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)-style
bundle: plain Markdown with YAML frontmatter, ordinary cross-links, and provenance. It is **the**
documentation for this repository.

It is reference knowledge, not memory. The repository is public, so there is no log, session
history, request record or to-do list here
([decision](decisions/the-repository-is-public-and-okf-is-reference-only.md)).

## Reading order

Stop as soon as you have what the task needs.

1. [`index.md`](index.md), the map.
2. [The overview](system/overview.md).
3. [Working in this repository](process/working-in-this-repository.md), before changing anything.
4. The [decisions](decisions/index.md) that govern the area you are touching.
5. The [specification](spec/index.md) section for that area.

## Layout

- [project/](project/index.md): the charter.
- [system/](system/index.md): the overview and repository map.
- [decisions/](decisions/index.md): architectural decision records.
- [spec/](spec/index.md): what is sent, and the roadmap.
- [operations/](operations/index.md): local development, releasing, the security checks.
- [process/](process/index.md): how work on the repository is done.
- [ontology.md](ontology.md): concept types, frontmatter and editing rules.
- [tools/](tools/index.md): the validator.

## Keeping it accurate

When a change makes a concept untrue, correct the concept in the same change and bump its
`generated.at`. Agents follow the skills in `.agents/skills/`: `okf-orient`, `okf-update` and
`okf-decision`. Validate before committing:

```sh
python3 okf/tools/validate_okf.py
```
