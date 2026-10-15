#!/usr/bin/env python3
"""Check that what is about to be published holds nothing private.

No secrets, no paths from someone's machine, no personal email addresses, no talk about a session,
no file where the repository does not keep files, and nothing on the maintainer's private deny
list (okf/operations/security-checks.md).

    scripts/check_publishable.py --staged          the commit being made (the pre-commit hook)
    scripts/check_publishable.py --message <file>  a commit message (the commit-msg hook)
    scripts/check_publishable.py --revs <revs...>  commits, as `git log` takes them: a push, a pull request
    scripts/check_publishable.py --all             the tracked tree and every commit on a publishable ref

A finding exits 1. In CI the matched text is not printed, so a log never repeats a leak.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SELF = "scripts/check_publishable.py"
CI = bool(os.environ.get("CI"))
REPO = Path(__file__).resolve().parent.parent

# ---- Where files may be ---------------------------------------------------------------------------

# Every top-level entry the repository keeps. A new one is added here, in the same commit.
TOP_LEVEL = {
    ".agents",
    ".claude",
    ".githooks",
    ".github",
    ".gitignore",
    "AGENTS.md",
    "CLAUDE.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "custom_components",
    "examples",
    "hacs.json",
    "okf",
    "pyproject.toml",
    "scripts",
    "tests",
    "uv.lock",
}
CLAUDE_DIR = (".claude/skills",)

# Documents live in okf/ and the few places the public-repository decision names.
DOC_PLACES = [
    re.compile(p)
    for p in (
        r"^okf/",
        r"^\.agents/skills/",
        r"^(AGENTS|CLAUDE|README|SECURITY)\.md$",
        r"(^|/)README\.md$",
        r"^\.github/",
    )
]
DOC_EXT = re.compile(r"\.(md|markdown|mdx|txt|log|rst|org)$", re.I)

NEVER = [
    (re.compile(r"(^|/)\.env(\.(?!example$)[^/]*)?$"), "an environment file"),
    (re.compile(r"^_private/"), "private working material"),
    (re.compile(r"(^|/)secrets\.yaml$"), "Home Assistant's secrets"),
    (re.compile(r"(^|/)\.storage/"), "Home Assistant's internal storage"),
    (re.compile(r"\.(pem|key|p12|pfx|jks|keystore|ppk)$", re.I), "a key or certificate"),
    (re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$"), "an SSH key"),
    (re.compile(r"\.(sqlite3?|db|db-wal|db-shm|dump|bak)$", re.I), "a database file"),
]

# Images (the blog's screenshots) only under docs' media folder, where each is reviewed before it is added.
MEDIA = re.compile(
    r"\.(png|jpe?g|gif|webp|avif|heic|bmp|tiff?|pdf|mp3|mp4|m4a|mov|webm|wav|zip|tar|tgz|gz|7z|docx?|xlsx?|pptx?)$",
    re.I,
)
MEDIA_PLACES = [re.compile(r"^okf/media/"), re.compile(r"^custom_components/honeycomb/brand/")]

MAX_BYTES = 1_000_000
BIG_OK = {"uv.lock"}

# ---- What text may not say ------------------------------------------------------------------------

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})\b")
EMAIL_LOCAL_OK = re.compile(r"^(no-?reply|git)$", re.I)
EMAIL_DOMAIN_OK = [
    re.compile(p, re.I)
    for p in (
        r"^example\.(com|net|org)$",
        r"\.(example|test|invalid|localhost)$",
        r"(^|\.)users\.noreply\.github\.com$",
        r"^anthropic\.com$",
        r"^\d+x\.[a-z]+$",
    )
]
EMAIL_ADDRESS_OK = {"noreply@anthropic.com", "support@github.com"}

LOCAL_PATH = re.compile(
    r"(?:^|[\s\"'`(=:,])((?:/Users|/home)/[A-Za-z0-9._-]+|[A-Za-z]:\\Users\\[^\\\s\"'`]+)"
)
PRIVATE_IP = re.compile(
    r"\b(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"
)
TAILNET = re.compile(r"\b[a-z0-9-]+\.tail[0-9a-f]{4,}\.ts\.net\b", re.I)
SESSION_TALK = re.compile(
    r"\b(as (you|the user|the maintainer) (asked|requested)|per (your|the user's) request|the user (asked|said|requested)|you asked me)\b",
    re.I,
)


def _email(line: str) -> str | None:
    for m in EMAIL.finditer(line):
        local = m.group(0).split("@")[0]
        if m.group(0).lower() in EMAIL_ADDRESS_OK:
            continue
        if not EMAIL_LOCAL_OK.match(local) and not any(r.search(m.group(1)) for r in EMAIL_DOMAIN_OK):
            return m.group(0)
    return None


def _deny_list() -> list[str]:
    """Words only the maintainer's checkout knows: names of a real home's people, rooms and devices.

    One per line in _private/deny.txt (ignored), or the file HONEYCOMB_HACS_DENY names. The list
    itself is never committed, because it is exactly what must not be published.
    """
    path = Path(os.environ.get("HONEYCOMB_HACS_DENY", REPO / "_private" / "deny.txt"))
    if not path.is_file():
        return []
    return [
        w.strip()
        for w in path.read_text(encoding="utf-8").splitlines()
        if w.strip() and not w.startswith("#")
    ]


DENY = [re.compile(rf"\b{re.escape(w)}\b", re.I) for w in _deny_list()]

CONTENT = [
    (
        "local-path",
        "an absolute path from someone's machine",
        lambda s: (m := LOCAL_PATH.search(s)) and m.group(1),
    ),
    ("email", "an email address that is not a synthetic one (use example.com)", _email),
    (
        "private-network",
        "an address on a private network; use example values",
        lambda s: (m := PRIVATE_IP.search(s)) and m.group(0),
    ),
    ("tailnet", "a Tailscale machine name", lambda s: (m := TAILNET.search(s)) and m.group(0)),
    (
        "session-talk",
        "talk about a session or a request; describe the change, not the conversation",
        lambda s: (m := SESSION_TALK.search(s)) and m.group(0),
    ),
    (
        "deny-list",
        "a word on the private deny list",
        lambda s: next((r.pattern for r in DENY if r.search(s)), None),
    ),
]
SKIP_CONTENT = {SELF, "uv.lock"}

# ---- Findings -------------------------------------------------------------------------------------

findings: list[tuple[str, str, str, str | None]] = []


def report(where: str, rule: str, why: str, match: str | None = None) -> None:
    findings.append((where, rule, why, match))


def check_never(path: str, where: str) -> None:
    for pattern, what in NEVER:
        if pattern.search(path):
            report(where, "never-commit", f"{what}, which is never committed")
    if MEDIA.search(path) and not any(r.search(path) for r in MEDIA_PLACES):
        report(
            where,
            "media",
            "an image, document, recording or archive outside okf/media/; these can carry real data",
        )


def check_path(path: str, where: str) -> None:
    top = path.split("/")[0]
    if top not in TOP_LEVEL:
        report(
            where,
            "top-level",
            f"a new top-level entry `{top}`; the repository keeps a fixed set (TOP_LEVEL in {SELF})",
        )
    if top == ".claude" and not any(path == p or path.startswith(p + "/") for p in CLAUDE_DIR):
        report(
            where, "agent-local", "a file in .claude/ besides the skills link; local agent settings stay out"
        )
    if DOC_EXT.search(path) and not any(r.search(path) for r in DOC_PLACES):
        report(
            where, "stray-document", "a document outside okf/ and the allowed places; notes go in _private/"
        )
    check_never(path, where)


def check_line(path: str, line_no: int, text: str, where: str) -> None:
    if path in SKIP_CONTENT:
        return
    for rule, why, find in CONTENT:
        if m := find(text):
            report(f"{where}{path + ':' if path else 'line '}{line_no}: ", rule, why, m)


# ---- Git ------------------------------------------------------------------------------------------


def git(*args: str, input: str | None = None) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args], input=input, capture_output=True, text=True, check=True
    ).stdout


def added_lines(args: list[str], where_prefix: bool) -> None:
    """Check every added line in `git log -p` or `git diff` output."""
    commit, file, line_no = "", None, 0
    for line in git(*args).splitlines():
        if line.startswith("\0commit "):
            commit, file = line[8:20] + " ", None
        elif line.startswith("+++ "):
            file = None if line == "+++ /dev/null" else line[6:]
        elif line.startswith("@@ "):
            line_no = int(m.group(1)) if (m := re.search(r"\+(\d+)", line)) else 0
        elif file and line.startswith("+"):
            check_line(file, line_no, line[1:], commit if where_prefix else "")
            line_no += 1
        elif file and not line.startswith(("-", "\\")):
            line_no += 1


PUBLISHABLE = ["--branches", "--tags", "--remotes", "--glob=refs/pull/*"]
LOG_PATCH = ["log", "-p", "-U0", "--no-color", "--no-ext-diff", "--no-renames", "--format=%x00commit %H"]


def blob_sizes(specs: list[str]) -> list[int]:
    if not specs:
        return []
    out = git("cat-file", "--batch-check=%(objectsize)", input="\n".join(specs) + "\n").splitlines()
    return [int(o) if o.isdigit() else 0 for o in out]


def check_new_files(revs: list[str]) -> None:
    out = git("log", "--no-renames", "--diff-filter=AC", "--name-only", "--format=%x00%H", *revs)
    files = []
    for block in filter(None, out.split("\0")):
        sha, *paths = [p for p in block.split("\n") if p]
        files += [(sha, p) for p in paths]
    for (sha, path), size in zip(files, blob_sizes([f"{s}:{p}" for s, p in files]), strict=True):
        where = f"{sha[:12]} {path}: "
        check_path(path, where)
        if path not in BIG_OK and size > MAX_BYTES:
            report(where, "large-file", "a file over 1 MB; large files are usually data")


def check_message(text: str, where: str) -> None:
    for i, line in enumerate(text.split("\n"), 1):
        if not line.startswith("#"):
            check_line("", i, line, where)


def check_messages(revs: list[str]) -> None:
    for block in filter(None, git("log", "--format=%x00%H%x1f%B", *revs).split("\0")):
        sha, _, body = block.partition("\x1f")
        check_message(body, f"{sha[:12]} commit message, ")


# ---- gitleaks -------------------------------------------------------------------------------------


def gitleaks(args: list[str], optional: bool = False, input: str | None = None) -> None:
    binary = shutil.which("gitleaks")
    if binary is None:
        if optional:
            print(
                "check_publishable: gitleaks is not installed; secrets are checked again in CI.",
                file=sys.stderr,
            )
            return
        sys.exit("check_publishable: gitleaks is required (brew install gitleaks)")
    leaks = 3
    r = subprocess.run(
        [
            binary,
            *args,
            "--config",
            str(REPO / ".github/gitleaks.toml"),
            "--exit-code",
            str(leaks),
            "--redact",
            "--no-banner",
            "--verbose",
            "--log-level",
            "warn",
        ],
        cwd=REPO,
        input=input,
        capture_output=True,
        text=True,
    )
    if r.returncode == leaks:
        sys.stdout.write(r.stdout)
        report("", "secret", "a secret (gitleaks; its findings are above, redacted)")
    elif r.returncode != 0:
        sys.exit(f"gitleaks failed: {r.stderr or r.stdout}")


# ---- Modes ----------------------------------------------------------------------------------------


def staged() -> None:
    for line in filter(
        None, git("diff", "--cached", "--name-status", "--no-renames", "--diff-filter=AC").split("\n")
    ):
        path = line.split("\t")[1]
        check_path(path, f"{path}: ")
        if path not in BIG_OK and blob_sizes([f":{path}"])[0] > MAX_BYTES:
            report(f"{path}: ", "large-file", "a file over 1 MB; large files are usually data")
    added_lines(["diff", "--cached", "-U0", "--no-color", "--no-ext-diff", "--no-renames"], False)
    gitleaks(["git", "--pre-commit", "--staged", "."], optional=True)


def message(file: str) -> None:
    text = re.split(r"^# -+ >8 -+$", Path(file).read_text(encoding="utf-8"), flags=re.M)[0]
    check_message(text, "commit message, ")
    gitleaks(["stdin"], optional=True, input=text)


def revs(rev_list: list[str]) -> None:
    if git("rev-list", "--count", *rev_list).strip() == "0":
        return
    check_new_files(rev_list)
    added_lines([*LOG_PATCH, *rev_list], True)
    check_messages(rev_list)
    gitleaks(["git", "--log-opts", " ".join(rev_list), "."])


def all_() -> None:
    for path in filter(None, git("ls-files").split("\n")):
        check_path(path, f"{path}: ")
        if path in SKIP_CONTENT or (REPO / path).is_symlink():
            continue
        try:
            data = (REPO / path).read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8000]:
            continue
        for i, line in enumerate(data.decode("utf-8", "replace").split("\n"), 1):
            check_line(path, i, line, "")
    if git("rev-list", "--count", *PUBLISHABLE).strip() != "0":
        check_new_files(PUBLISHABLE)
        added_lines([*LOG_PATCH, *PUBLISHABLE], True)
        check_messages(PUBLISHABLE)
        gitleaks(["git", "--log-opts", " ".join(PUBLISHABLE), "."])


def main(argv: list[str]) -> int:
    mode, *rest = argv or [""]
    if mode == "--staged":
        staged()
    elif mode == "--message" and rest:
        message(rest[0])
    elif mode == "--revs" and rest:
        revs(rest)
    elif mode == "--all":
        all_()
    else:
        print(__doc__, file=sys.stderr)
        return 2

    seen, unique = set(), []
    for f in findings:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    if not unique:
        return 0
    print(
        f"\ncheck_publishable: {len(unique)} finding{'s' if len(unique) != 1 else ''}; this repository is public.\n",
        file=sys.stderr,
    )
    for where, rule, why, match in unique:
        print(f"  {where}{rule}: {why}" + (f"\n      {match}" if match and not CI else ""), file=sys.stderr)
    print(
        "\nFix the content: private notes go in _private/ (ignored), use example values, and describe the\n"
        f"change rather than the conversation. A false positive is fixed in the rules of {SELF} in the\n"
        "same commit. Never bypass the check with --no-verify.\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
