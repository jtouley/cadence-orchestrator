"""Tests for checks/leak_check.py. Sample leaks are assembled at runtime so this file passes the check itself."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECK = os.path.join(ROOT, "checks", "leak_check.py")
sys.path.insert(0, os.path.dirname(CHECK))
import leak_check  # noqa: E402

AT = "@"
UUID = "-".join(["1b2c3d4e", "5f60", "4a7b", "8c9d", "0e1f2a3b4c5d"])
LOG_DIR = "session" + "_log"


def found(text, path="f.md"):
    return leak_check.findings(path, text)


def test_emails_blocked_except_allowlist():
    assert found(f"contact jane.doe{AT}corp.io")
    assert found(f"<Jane{AT}Mail.Example.co.uk>")
    for ok in (
        f"noreply{AT}anthropic.com",
        f"user{AT}example.com",
        f"git{AT}github.com:o/r.git",
        "    @pytest.fixture",
        f"x{AT}pytest.mark",
        "@types/node",
        "npm i @anthropic-ai/sdk",
    ):
        assert not found(ok), ok


def test_account_uuids_next_to_keys():
    for key in ("organizationUuid", "organization_uuid", "account_uuid", "accountUuid", "org_id"):
        assert found(f'"{key}": "{UUID}"'), key
        assert found(f"{key}={UUID}"), key
    assert not found(f'"request_id": "{UUID}"')  # a UUID alone isn't flagged


def test_session_log_paths_and_files():
    assert found(f"see {LOG_DIR}/2026-10-31.jsonl")
    assert found("", path=f"notes/{LOG_DIR}/a.txt")
    assert found("", path=f"{LOG_DIR}/a.txt")
    assert not found(f"the {LOG_DIR} folder is ignored")


def test_cli_and_repo_is_clean():
    d = tempfile.mkdtemp()
    bad = os.path.join(d, "bad.txt")
    open(bad, "w").write(f"ping me: someone{AT}corp.io\n")
    out = subprocess.run([sys.executable, CHECK, bad], capture_output=True, text=True)
    assert out.returncode == 1 and "email address" in out.stderr
    files = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True, text=True).stdout.split()
    clean = subprocess.run([sys.executable, CHECK, *files], cwd=ROOT, capture_output=True, text=True)
    assert clean.returncode == 0, clean.stderr
