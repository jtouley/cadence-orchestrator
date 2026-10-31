#!/usr/bin/env bash
# Vendor the tpm kit into a repo:  ./install.sh --target <claude|codex|cursor|copilot|gemini|all> [--repo <path>]
set -euo pipefail
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/tools/install.py" "$@"
