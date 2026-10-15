---
name: make-a-release
description: Release a version of the Honeycomb integration so HACS offers it. Use when asked to release, tag, publish or ship a version, or to make a change available to users through HACS.
---

# Make a release

The procedure is `okf/operations/releasing.md`. Read it first.

1. `git pull --rebase --autostash`; `main` must be green in CI (`gh run list --branch main -L 3`).
2. Choose the version with the person: what changed since the last tag
   (`git log $(git describe --tags --abbrev=0)..HEAD --oneline`, or everything if there is no tag).
3. Set it in `custom_components/honeycomb/manifest.json` and `pyproject.toml`; update the roadmap's
   status table if the release completes a part. Commit and push.
4. `gh release create v<version> --title v<version> --generate-notes`, then rewrite the notes for
   someone running a home: what they will see, what they must do. Publishing is outward-facing:
   confirm with the person before running it.
5. Never move or delete a published release; a fix is a new version.
