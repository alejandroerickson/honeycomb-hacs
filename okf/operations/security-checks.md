---
type: Process
title: The checks that keep private material out of the repository
description: What the privacy check refuses, where it runs, the private deny list, and what to do if something leaks.
tags: [operations, security, public, privacy]
generated: {by: agent:claude, at: 2026-10-14}
status: stable
---

# Security checks

## What is refused

`scripts/check_publishable.py` refuses, in files, added lines and commit messages:

- secrets (gitleaks, with `.github/gitleaks.toml`);
- `.env` files, `_private/`, Home Assistant's `secrets.yaml` and `.storage/`, keys, databases;
- absolute paths from a machine, email addresses other than synthetic and no-reply ones, private
  network addresses (`192.168.*`, `10.*`, `172.16-31.*`) and Tailscale machine names;
- talk about a session or a request, instead of the change;
- a file in a top-level place the repository does not keep, a document outside `okf/` and the
  allowed places, an image outside `okf/media/`, a file over 1 MB;
- any word on the **private deny list**.

## The private deny list

Names of a real home's people, rooms and devices cannot be in the check's rules, because the rules
are published. The check reads them from `_private/deny.txt` in the maintainer's checkout (ignored
by git), or from the file `HONEYCOMB_HACS_DENY` names: one word or phrase per line, `#` for
comments. CI has no deny list; the hooks are where it applies, so they must be on.

## Where it runs

| When | How |
|---|---|
| Each commit | `.githooks/pre-commit` (`--staged`) and `commit-msg` (`--message`) |
| Each push | `.githooks/pre-push` (`--revs`) on every commit the push carries |
| Each pull request and push to `main` | the CI job "Nothing private" |
| Weekly | the Security workflow, `--all`: the tree and every published commit |

`scripts/bootstrap.sh` turns the hooks on (`git config core.hooksPath .githooks`). GitHub's secret
scanning and push protection are on for the repository as well.

## Run it by hand

```sh
python3 scripts/check_publishable.py --all
```

## If something private was published

1. **A secret:** revoke it where it was issued first. Rewriting history does not unpublish it.
2. Tell the maintainer what it is and where (commit, file, line), without quoting it.
3. Fix the rule in `scripts/check_publishable.py` that should have caught it, in the same commit as
   the fix.
4. Rewriting history needs the maintainer's yes, and the `protect-main` ruleset lifted by them.
