#!/usr/bin/env bash
# Install every target into a scratch git repo twice; fail if the second run changes any file.
set -euo pipefail
repo="$(mktemp -d)"
git init -q "$repo"
snapshot() { (cd "$repo" && find . -path ./.git -prune -o -type f -print0 | sort -z | xargs -0 sha256sum); }
node bin/cadence-orchestrator.mjs --target all --repo "$repo"
before="$(snapshot)"
node bin/cadence-orchestrator.mjs --target all --repo "$repo" >/dev/null
after="$(snapshot)"
if ! diff <(echo "$before") <(echo "$after"); then
  echo "The second install changed files (diff above)." >&2
  exit 1
fi
echo "Second run changed nothing ($(echo "$after" | wc -l) files)."
