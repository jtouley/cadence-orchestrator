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


def test_skill_version_matches_the_package_version():
    import json

    version = json.load(open(os.path.join(ROOT, "package.json")))["version"]
    assert frontmatter(SKILL_DIR)["metadata"]["version"] == version
    # The README ships on the npm page: any "Version X.Y.Z" there must be the package version.
    readme = open(os.path.join(ROOT, "README.md")).read()
    for stated in re.findall(r"\bVersion (\d+\.\d+\.\d+)", readme):
        assert stated == version, f"README says Version {stated}, package.json says {version}"


def _flat(path):
    return " ".join(open(path).read().split())


def _paragraphs(path):
    return [" ".join(p.split()) for p in re.split(r"\n\s*\n|\n(?=\s*(?:- |\| |\d+\. ))", open(path).read())]


def test_only_step_5_spells_out_a_reviewer_prompt():
    # One full statement of the reviewer-prompt rule, so copies can't drift; other places point to step 5.
    skill = _flat(os.path.join(SKILL_DIR, "SKILL.md"))
    assert skill.count("standard and destination") == 1
    step5 = skill[skill.index("5. **Verify independently") : skill.index("6. **Report.**")]
    assert "standard and destination" in step5
    dispatch = skill[skill.index("## Dispatch prompts") : skill.index("**Pin the doc**")]
    assert "step 5" in dispatch and "no out-of-scope line" in dispatch


def test_out_of_scope_lines_are_for_builders_and_investigators_only():
    # Wherever a doc says a prompt names what's out, it says whose prompt, and it isn't a reviewer's.
    docs = [os.path.join(SKILL_DIR, "SKILL.md"), os.path.join(SKILL_DIR, "references", "sources.md")]
    docs.append(os.path.join(ROOT, "README.md"))
    for doc in docs:
        for para in _paragraphs(doc):
            low = para.lower()
            if re.search(r"(names?|states?|says?) what'?s out|what'?s out of scope|scope boundary", low):
                assert re.search(r"builder|investigator", low), (doc, para[:120])
                assert not re.search(r"every (subagent )?prompt|the prompt names", low), (doc, para[:120])


def test_quality_pass_is_never_skipped_or_narrowed():
    skill = _flat(os.path.join(SKILL_DIR, "SKILL.md"))
    step5 = skill[skill.index("5. **Verify independently") : skill.index("6. **Report.**")]
    sentence = re.search(r"The quality pass [^.]*\.", step5).group(0)
    assert "never skipped" in sentence and "narrowed" in sentence
    # in the same sentence: consistent with the parallel split and with round two's review of the new commit range
    assert "parallel" in sentence and "new commit range" in sentence
    # the PR #11 reviewer rule is still here
    assert "Leave out suspected issues, focus areas, what a fix does, earlier findings" in step5
    assert "Builders fixing blockers get the findings verbatim." in step5
