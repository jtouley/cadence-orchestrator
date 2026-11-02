#!/usr/bin/env python3
"""Fail if CI's gitleaks version differs from the gitleaks hook rev in .pre-commit-config.yaml.

Dependabot bumps the hook rev but not ci.yml, so without this the "same version as the pre-commit hook" scan would
drift. Usage: check_gitleaks_version.py [ci.yml] [.pre-commit-config.yaml]
"""

from __future__ import annotations

import re
import sys


def ci_version(text: str) -> str | None:
    m = re.search(r'GITLEAKS_VERSION:\s*"?v?([0-9][0-9A-Za-z.\-]*)"?', text)
    return m.group(1) if m else None


def hook_version(text: str) -> str | None:
    m = re.search(
        r"repo:\s*https://github\.com/gitleaks/gitleaks\s*\n\s*rev:\s*v?([0-9][0-9A-Za-z.\-]*)", text
    )
    return m.group(1) if m else None


def main(argv: list[str]) -> int:
    ci_path = argv[0] if argv else ".github/workflows/ci.yml"
    hook_path = argv[1] if len(argv) > 1 else ".pre-commit-config.yaml"
    ci, hook = ci_version(open(ci_path).read()), hook_version(open(hook_path).read())
    if not ci or not hook:
        print(f"gitleaks version not found (ci.yml: {ci}, pre-commit: {hook})", file=sys.stderr)
        return 1
    if ci != hook:
        print(
            f"gitleaks drift: ci.yml installs {ci}, the pre-commit hook uses {hook}. Update GITLEAKS_VERSION and "
            "GITLEAKS_SHA256 in ci.yml (sha256 from the release's checksums file).",
            file=sys.stderr,
        )
        return 1
    print(f"gitleaks {ci} in both ci.yml and .pre-commit-config.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
