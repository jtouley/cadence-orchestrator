#!/usr/bin/env bash
# Vendor the tpm kit into a repo:  ./install.sh [--target <antigravity|claude|codex|copilot|cursor|gemini|all>] [--repo <path>]
# Without --target it installs for each editor the repo has config for.
# Thin wrapper over the one installer, bin/cadence-orchestrator.mjs (the same one `npx cadence-orchestrator` runs).
set -euo pipefail
exec node "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/bin/cadence-orchestrator.mjs" "$@"
