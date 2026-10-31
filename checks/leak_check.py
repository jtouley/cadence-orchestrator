#!/usr/bin/env python3
"""Block commits that would leak personal or account data.

Checks each file given (path and content) for:
- email addresses, except an allowlist (noreply@anthropic.com, example domains
  and their subdomains, git@ SSH remotes on GitHub, GitLab and Bitbucket);
- Anthropic organization/account UUIDs: a UUID next to a key such as
  organizationUuid or account_uuid;
- session log directories (a path component named session_log).

Used as a pre-commit hook here and on the orchestration branch, and in CI.
Stdlib only. Exit 0 if clean, 1 with one line per finding otherwise.
"""

from __future__ import annotations

import re
import sys

EMAIL = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")
ALLOWED_EMAILS = {"noreply@anthropic.com"}
ALLOWED_DOMAINS = {"example.com", "example.org", "example.net"}
GIT_HOSTS = {"github.com", "gitlab.com", "bitbucket.org"}  # git@<host>:owner/repo SSH remotes
CODE_DOMAINS = ("pytest.",)  # decorator-like code such as x@pytest.fixture
UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
# Any key containing account/org(anization) + uuid/id, e.g. user_account_uuid or orgUuid.
ACCOUNT_KEY = r"[\w-]*(?:organi[sz]ation|org|account)[_-]?(?:uuid|id)[\w-]*"
ACCOUNT_UUID = re.compile(rf"(?i){ACCOUNT_KEY}[\"']?\s*[:=]\s*[\"']?{UUID}")
SESSION_LOG = re.compile(r"(?:^|[\\/\s\"'`(])session_log[\\/]")


def email_ok(address: str) -> bool:
    local, _, domain = address.lower().partition("@")
    return (
        address.lower() in ALLOWED_EMAILS
        or any(domain == d or domain.endswith("." + d) for d in ALLOWED_DOMAINS)
        or (local == "git" and domain in GIT_HOSTS)
        or domain.startswith(CODE_DOMAINS)
    )


def findings(path: str, text: str) -> list[str]:
    out = []
    if SESSION_LOG.search("/" + path):
        out.append(f"{path}: file is inside a session_log directory")
    for n, line in enumerate(text.splitlines(), 1):
        for m in EMAIL.finditer(line):
            if not email_ok(m.group(0)):
                out.append(f"{path}:{n}: email address {m.group(0)}")
        if ACCOUNT_UUID.search(line):
            out.append(f"{path}:{n}: organization/account UUID")
        if SESSION_LOG.search(line):
            out.append(f"{path}:{n}: session_log path")
    return out


def main(argv: list[str]) -> int:
    problems = []
    for path in argv:
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            text = ""  # binary or unreadable: only the path is checked
        problems += findings(path, text)
    for p in problems:
        print(p, file=sys.stderr)
    if problems:
        print(
            "leak check: remove these or, for a false positive, extend the allowlist in checks/leak_check.py.",
            file=sys.stderr,
        )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
