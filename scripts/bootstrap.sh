#!/bin/sh
# Set up a checkout: the development environment and the git hooks that keep private material out
# of this public repository (okf/operations/local-development.md).
set -eu
cd "$(dirname "$0")/.."
git config core.hooksPath .githooks
uv sync
command -v gitleaks >/dev/null || echo "bootstrap: install gitleaks (brew install gitleaks) so commits are checked for secrets."
echo "bootstrap: ready. Run the tests with: uv run pytest"
