---
name: okf-update
description: Keep honeycomb-hacs's okf/ documentation true, and write or revise any concept in it. Use before finishing any change to the integration, tests, tooling, CI or process; when asked to document something; and whenever something in okf/ no longer matches the code.
---

# Keep the okf/ bundle true

**A change that makes a concept untrue fixes that concept in the same change.** Correct what is
there in preference to adding a near-duplicate.

## Procedure

1. List what changed: `git status --short`, `git diff --name-only`.
2. Find the affected concepts with the impact map below, and grep `okf/` for names you renamed or
   removed.
3. Correct each in place, in the present tense. Do not describe how it came to be.
4. A durable choice gets a decision record (`okf-decision`).
5. Update the roadmap's status table, its date, and its open questions.
6. On every concept you edit, set `generated` to `{by: agent:<your-name>, at: <YYYY-MM-DD>}`;
   keep `status` accurate (`draft` until reviewed).
7. A new file gets a line in its directory's `index.md`. A new concept type gets a row in
   `okf/ontology.md` and in `TYPES` in `okf/tools/validate_okf.py`.
8. Outside the bundle: `AGENTS.md`, `README.md`, and these skills, if the change touches them.
9. `python3 okf/tools/validate_okf.py` reports 0 errors.
10. Reread what you wrote for session talk, private names and anything from a real home. The hooks
    catch patterns, not judgement.

## Impact map

| When you change | Check |
|---|---|
| What becomes a span, its name or attributes, exclusions, delivery | `spec/01-telemetry.md`, `README.md`, the roadmap |
| `config_flow.py`, `strings.json`, options | `system/overview.md`, `README.md` (Install) |
| A new file in `custom_components/honeycomb/` | `system/overview.md` (Parts) |
| `manifest.json` requirements, the sender | decision `no-requirements-beyond-home-assistant` |
| Anything read from Home Assistant | decision `only-public-home-assistant-interfaces` |
| Default exclusions | decision `sensitive-data-stays-home-by-default`, `spec/01` §1.5 |
| `hacs.json`, versions, releasing | `operations/releasing.md` |
| `pyproject.toml`, `scripts/bootstrap.sh`, `.github/workflows/ci.yml` | `operations/local-development.md` |
| `scripts/check_publishable.py`, `.githooks/`, `security.yml`, `gitleaks.toml`, `SECURITY.md` | `operations/security-checks.md` |
| A new top-level entry | `system/overview.md`, `AGENTS.md`, `TOP_LEVEL` in `scripts/check_publishable.py` |
| How work is done | `process/working-in-this-repository.md`, `AGENTS.md` |

## Where knowledge goes

Templates and conventions per type are in `references/concept-types.md`.

## Never put in the bundle

Session history, task logs, handoff notes, requests, to-do lists, private names, local paths,
secrets, anything from a real home, or a proposal written as though it were decided.
`okf/log.md` is gitignored on purpose.
