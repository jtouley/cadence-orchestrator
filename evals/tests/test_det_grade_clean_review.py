"""Tests for evals/scripts/det_grade_clean_review.py on small fixture runs: saved prompts, an optional transcript.

Run with `pytest`. Standard library only.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

EVALS = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("det_grade", EVALS / "scripts" / "det_grade_clean_review.py")
det = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(det)

ROUND2 = "second-round-hides-prior-findings"
FIRST = "first-review-hides-suspected-bug"

CLEAN_REVIEW = "/code-review on main..feature/search-api and comment the full review to GitHub."
LEAKY_REVIEW = (
    "/code-review on main..feature/search-api. Round one found R1-1: the offset cursor skips a row on every page "
    "boundary; it was fixed with keyset pagination. Comment the full review to GitHub."
)
FIX_CHECK = (
    "Check out feature/search-api at round-2. Don't review the branch; for each finding run its repro and report "
    "whether it still reproduces.\n"
    "- R1-1 (high): the offset cursor skips a row on every page boundary, because the next token advances by "
    "page_size - 1. Repro: python repro/r1_1_cursor_gap.py <clone>\n"
    '- R1-2 (medium): LIKE wildcards in the search term aren\'t escaped, so searching "100%" also matches '
    '"1000 done". Repro: python repro/r1_2_like_wildcard.py <clone>'
)
COMBINED = (
    "Review main..feature/search-api and also confirm the round-one fixes.\n" + FIX_CHECK.split("\n", 1)[1]
)


def run(prompts: list[str], case: str = ROUND2, transcript: bool = True) -> dict:
    rd = Path(tempfile.mkdtemp())
    (rd / "outputs").mkdir()
    for i, p in enumerate(prompts, 1):
        (rd / "outputs" / f"subagent-prompt-{i:02}.md").write_text(p)
    if transcript:
        events = [
            {
                "type": "assistant",
                "message": {"content": [{"type": "tool_use", "name": "Agent", "input": {"prompt": p}}]},
            }
            for p in prompts
        ]
        # a tool_use with no input must not break the scan
        events.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Agent"}]}})
        (rd / "transcript.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n")
    return det.grade(str(rd), case)


def verdicts(result: dict) -> list[bool]:
    return [r["passed"] for r in result["results"] if r["kind"] == "deterministic"]


def test_clean_review_and_proper_fix_check_pass_every_check():
    result = run([CLEAN_REVIEW, FIX_CHECK])
    assert verdicts(result) == [True] * 5, result
    assert all(r.get("passed_transcript_scan") in (True, None) for r in result["results"])


def test_leaky_review_fails_the_leak_checks():
    v = verdicts(run([LEAKY_REVIEW, FIX_CHECK]))
    assert v[0] and v[1], v  # target named, fix check complete
    assert v[2:] == [False, False, False], v  # finding id, finding text, fix description


def test_combined_review_and_repro_prompt_fails():
    """One prompt that asks for a review and carries the findings is a review, so the leak checks see it and no
    fix check exists."""
    v = verdicts(run([COMBINED]))
    assert not v[1], "a combined prompt isn't a fix check"
    assert not all(v[2:]), v


def test_fix_description_in_a_fix_check_fails():
    v = verdicts(run([CLEAN_REVIEW, FIX_CHECK + "\nThe fix uses keyset pagination and escape_like()."]))
    assert v[4] is False, v


def test_empty_prompt_set_fails():
    assert verdicts(run([])) == [False] * 5
    assert verdicts(run([], case=FIRST)) == [False] * 4
    # only a fix check: every review-scoped check has nothing to look at
    v = verdicts(run([FIX_CHECK]))
    assert v[0] is False and v[2] is False and v[3] is False, v


def test_missing_transcript_reports_na_and_still_grades():
    result = run([CLEAN_REVIEW, FIX_CHECK], transcript=False)
    assert result["transcript_agent_calls"] is None
    assert verdicts(result) == [True] * 5
    det_rows = [r for r in result["results"] if r["kind"] == "deterministic"]
    assert all(r["passed_transcript_scan"] is None and "n/a" in r["evidence"] for r in det_rows)
