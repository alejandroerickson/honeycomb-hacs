---
name: audit-for-leaks
description: Check everything this public repository holds (every branch and tag, pull request and issue text, release notes) for secrets and private material, especially anything from a real home, and deal with what is found. Use when asked to audit, scan or check the repository or its history for secrets, leaks or personal details, and when something private may have been committed or pushed.
---

# Audit for leaks

The knowledge is in `okf/operations/security-checks.md`. Read it before the first command.

## What must stay true

- **Work outside the repository.** Mirror clones and reports go in a fresh temporary folder,
  deleted afterwards.
- **Never repeat a leak.** Report a finding by place (commit, file, line, rule), never by quoting
  it.
- **A secret is revoked before anything else.** Removing it from history does not unpublish it.
- **Rewriting history and force-pushing are the person's calls.** Say what each would do, then
  wait for their yes.

## Procedure

1. `python3 scripts/check_publishable.py --all` in the maintainer's checkout, so the private deny
   list applies.
2. Everything GitHub holds: `git clone --mirror` into a temporary folder and run the check with
   `HONEYCOMB_HACS_DENY` pointing at the deny list, from the checkout's script against the mirror;
   read pull request, issue and release text with `gh`.
3. Read what no pattern catches: screenshots (entity names, times, places), example
   configurations, and commit messages, for anything from a real home.
4. Report each finding by place and kind, what it exposes, and the remedy from the guide.
