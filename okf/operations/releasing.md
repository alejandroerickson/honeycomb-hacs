---
type: Process
title: Releasing a version
description: How a version is numbered, tagged and published so HACS offers it.
tags: [operations, release, hacs]
generated: {by: agent:claude, at: 2026-10-14}
status: stable
---

# Releasing

HACS offers an integration's GitHub releases; a user installs or updates to a tag
([decision](../decisions/releases-are-github-releases-hacs-installs.md)).

1. `main` is green in CI.
2. Set `version` in `custom_components/honeycomb/manifest.json` (and `pyproject.toml`) to the new
   version, [semantic versioning](https://semver.org/): a change to what is sent, or to a default
   exclusion, is at least a minor version.
3. Commit, push, then tag and publish:

   ```sh
   gh release create v<version> --title v<version> --generate-notes
   ```

4. Read the generated notes and rewrite them for someone running a home: what they will see, and
   anything they must do.

A release is never moved or deleted once published; a fix is a new version.
