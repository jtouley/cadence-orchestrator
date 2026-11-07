"""CI's gitleaks must be the version the pre-commit hook uses (Dependabot only bumps the hook)."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, ".github", "scripts", "check_gitleaks_version.py")
CI = os.path.join(ROOT, ".github", "workflows", "ci.yml")
HOOKS = os.path.join(ROOT, ".pre-commit-config.yaml")


def run(*args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)


def test_repo_gitleaks_versions_match():
    out = run(CI, HOOKS)
    assert out.returncode == 0, out.stderr
    assert "gitleaks 8.30.1" in out.stdout


def test_drift_is_caught():
    d = tempfile.mkdtemp()
    bumped = os.path.join(d, "pre-commit.yaml")
    text = open(HOOKS).read()
    open(bumped, "w").write(text.replace("rev: v8.30.1", "rev: v8.31.0"))
    out = run(CI, bumped)
    assert (
        out.returncode == 1
        and "gitleaks drift: ci.yml installs 8.30.1, the pre-commit hook uses 8.31.0" in out.stderr
    )


def test_ci_verifies_the_tarball_checksum():
    text = open(CI).read()
    assert 'GITLEAKS_SHA256: "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"' in text
    assert "sha256sum -c -" in text and "go install" not in text and "setup-go" not in text


def test_release_installs_npm_with_npm_ci_from_the_pinned_lockfile():
    import json
    import re

    text = open(os.path.join(ROOT, ".github", "workflows", "release.yml")).read()
    # Scorecard's Pinned-Dependencies accepts `npm ci`; `npm install`/`npm i` of a package is flagged.
    assert "npm ci --ignore-scripts" in text
    assert not re.search(r"\bnpm (install|i|update)\b", text)
    lock = json.load(open(os.path.join(ROOT, ".github", "npm", "package-lock.json")))["packages"][
        "node_modules/npm"
    ]
    version = re.search(r'NPM_VERSION: "([^"]+)"', text).group(1)
    integrity = re.search(r'NPM_INTEGRITY: "([^"]+)"', text).group(1)
    assert (lock["version"], lock["integrity"]) == (version, integrity)
