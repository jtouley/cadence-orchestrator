"""The shipped skill follows the Agent Skills specification (https://agentskills.io/specification).

These checks mirror the spec's frontmatter rules and the reference validator (skills-ref) without depending on it,
so they run in CI. Run `skills-ref validate skills/tpm` for the authoritative check.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(ROOT, "skills", "tpm")
CLI = os.path.join(ROOT, "bin", "cadence-orchestrator.mjs")
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}


def frontmatter(skill_dir):
    text = open(os.path.join(skill_dir, "SKILL.md")).read()
    assert text.startswith("---\n")
    block = text[4 : text.index("\n---\n", 4)]
    fields, current = {}, None
    for line in block.splitlines():
        if line.startswith("  ") and current == "metadata":
            key, _, value = line.strip().partition(": ")
            fields["metadata"][key] = value.strip('"')
        elif line and not line.startswith(" "):
            current, _, value = line.partition(":")
            fields[current] = {} if current == "metadata" else value.strip()
    return fields


def problems(skill_dir, allow_extra=()):
    fm = frontmatter(skill_dir)
    out = []
    extra = set(fm) - SPEC_FIELDS - set(allow_extra)
    if extra:
        out.append(f"non-spec fields: {sorted(extra)}")
    name = fm.get("name", "")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) or len(name) > 64:
        out.append(f"bad name {name!r}")
    if os.path.basename(skill_dir) != name:
        out.append("directory name doesn't match name")
    if not 1 <= len(fm.get("description", "")) <= 1024:
        out.append("description length")
    if "compatibility" in fm and not 1 <= len(fm["compatibility"]) <= 500:
        out.append("compatibility length")
    if not all(isinstance(v, str) for v in fm.get("metadata", {}).values()):
        out.append("metadata values must be strings")
    return out


def test_shipped_skill_follows_the_spec():
    assert problems(SKILL_DIR) == []
    lines = open(os.path.join(SKILL_DIR, "SKILL.md")).read().count("\n")
    assert lines < 500  # the spec's recommended maximum
    for sub in ("scripts", "references"):
        assert os.path.isdir(os.path.join(SKILL_DIR, sub))


def test_file_references_are_relative_and_exist():
    text = open(os.path.join(SKILL_DIR, "SKILL.md")).read()
    refs = set(re.findall(r"`((?:references|scripts)/[\w./-]+)`", text))
    assert refs, "expected references to bundled files"
    for ref in refs:
        assert os.path.exists(os.path.join(SKILL_DIR, ref)), ref


def test_skill_body_names_no_client_specific_tools():
    text = open(os.path.join(SKILL_DIR, "SKILL.md")).read().split("\n---\n", 1)[1]
    for word in ("TodoWrite", "Agent tool", "Task tool", "Bash tool", "Glob", "MultiEdit", "mcp__"):
        assert word not in text, word


def test_vendored_copies_follow_the_spec_except_claude_only_keys():
    repo = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", repo], check=True)
    subprocess.run([CLI, "--target", "all", "--repo", repo], check=True, capture_output=True)
    for skills in (".agents/skills/tpm", ".github/skills/tpm"):
        assert problems(os.path.join(repo, skills)) == [], skills
    claude = os.path.join(repo, ".claude/skills/tpm")
    assert problems(claude, allow_extra=("disable-model-invocation",)) == []
    assert frontmatter(claude)["disable-model-invocation"] == "true"
    assert "disable-model-invocation" not in frontmatter(SKILL_DIR)
