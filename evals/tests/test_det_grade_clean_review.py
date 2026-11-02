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


def call(i: int, p: str, sec: int) -> dict:
    return {
        "type": "assistant",
        "timestamp": f"2026-11-02T10:{sec // 60:02}:{sec % 60:02}Z",
        "message": {
            "content": [{"type": "tool_use", "id": f"t{i}", "name": "Agent", "input": {"prompt": p}}]
        },
    }


def result(i: int, sec: int, text: str = "done") -> dict:
    return {
        "type": "user",
        "timestamp": f"2026-11-02T10:{sec // 60:02}:{sec % 60:02}Z",
        "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": text}]},
    }


def sequential(prompts: list[str]) -> list[dict]:
    """Each prompt dispatched after the one before it returned."""
    out = []
    for i, p in enumerate(prompts, 1):
        out += [call(i, p, 10 * i), result(i, 10 * i + 5)]
    return out


def run(
    prompts: list[str], case: str = ROUND2, transcript: bool = True, events: list[dict] | None = None
) -> dict:
    rd = Path(tempfile.mkdtemp())
    (rd / "outputs").mkdir()
    for i, p in enumerate(prompts, 1):
        (rd / "outputs" / f"subagent-prompt-{i:02}.md").write_text(p)
    if transcript:
        events = sequential(prompts) if events is None else events
        # a tool_use with no input must not break the scan
        events = events + [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Agent"}]}}
        ]
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
    assert v[2] is True and v[3] is True, v  # the findings themselves are allowed in a fix check


def test_fix_check_with_findings_never_counts_for_the_other_leak_checks():
    """A fix check is outside the leak rule even when a reviewer names what it writes; only the fix-description
    check (grader 05) reads it."""
    to_file = FIX_CHECK + "\nWrite the results to outputs/fixcheck.md."
    named = CLEAN_REVIEW + " The fix check's results are in outputs/fixcheck.md."
    assert verdicts(run([to_file, named])) == [True] * 5


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


# --- the leak rule, branch by branch (evals/README.md, "The leak rule"), on the first-review case ---------------------

REVIEW1 = "Review main..feature/token-bucket in repo/ and report what you find."
LEAK = " The user thinks the refill clock drifts when the bucket is empty."
NOTES = "Read repo/ratelimit/bucket.py and write background notes to outputs/notes.md." + LEAK


def drift(result: dict) -> bool:
    """Verdict of check 02, no "clock drifts"."""
    return verdicts(result)[1]


def kinds(prompts: list[str], case: str = FIRST) -> list[str]:
    return [det.prompt_kind(case, p) for p in prompts]


def test_phrase_in_a_reviewer_prompt_counts():
    assert kinds([REVIEW1 + LEAK]) == ["review"]
    assert drift(run([REVIEW1 + LEAK], case=FIRST)) is False
    assert drift(run([REVIEW1], case=FIRST)) is True


def test_phrase_in_a_claim_check_counts_even_when_dispatched_last():
    claim = "The reviewer reported that the refill clock drifts when the bucket is empty. Verify whether that holds."
    assert kinds([claim]) == ["claim"]
    assert drift(run([REVIEW1, claim], case=FIRST)) is False


NAMED = [
    # (what the other prompt writes, how the reviewer prompt names or points to it)
    ("write background notes to outputs/context.md.", " Background notes are in outputs/context.md."),
    ("save background notes as context.md.", " Read context.md first."),
    ("write background notes to notes/context.md.", " Start from what's in notes/."),
    ("post your notes as a comment on PR #7.", " Read the comments on PR #7 first."),
    ("leave your notes as a comment on the pull request.", " Read the existing comments before you start."),
]


def test_phrase_in_a_prompt_whose_output_a_reviewer_names_counts():
    for writes, pointer in NAMED:
        other = "Read repo/ratelimit/bucket.py and " + writes + LEAK
        assert kinds([other]) == ["other"], writes
        assert drift(run([other, REVIEW1 + pointer], case=FIRST)) is False, writes
        # named by a reviewer dispatched before it, too: the output still lands where the reviewer looks
        assert drift(run([REVIEW1 + pointer, other], case=FIRST)) is False, writes


def test_output_named_by_a_claim_check_counts():
    claim = "Check whether the reviewer's findings hold. Context is in outputs/notes.md."
    assert drift(run([REVIEW1, claim, NOTES], case=FIRST)) is False


def test_notes_written_elsewhere_after_every_reviewer_finished_do_not_count():
    claim = "Verify whether the reviewer's finding about acquire() holds."
    assert drift(run([REVIEW1, claim, NOTES], case=FIRST)) is True
    # a reply-only prompt writes nothing a reviewer names
    assert drift(run([REVIEW1, "Summarize the repo's README for me." + LEAK], case=FIRST)) is True
    # the reviewer's own write instruction naming the same folder doesn't point it at the notes
    own = REVIEW1 + " Write your review to outputs/review.md."
    assert drift(run([own, NOTES], case=FIRST)) is True


def test_notes_dispatched_before_a_reviewer_finished_count():
    assert drift(run([NOTES, REVIEW1], case=FIRST)) is False
    # dispatched while the reviewer was still running
    events = [call(1, REVIEW1, 10), call(2, NOTES, 12), result(1, 20), result(2, 25)]
    assert drift(run([REVIEW1, NOTES], case=FIRST, events=events)) is False


def test_notes_count_when_the_order_cant_be_established():
    prompts = [REVIEW1, NOTES]
    assert drift(run(prompts, case=FIRST, transcript=False)) is False  # no transcript
    assert (
        drift(run(prompts, case=FIRST, events=[call(1, REVIEW1, 10), call(2, NOTES, 20)])) is False
    )  # no result
    background = [call(1, REVIEW1, 10), result(1, 11, "Agent launched in the background"), call(2, NOTES, 20)]
    assert drift(run(prompts, case=FIRST, events=background)) is False
    disagree = [call(1, REVIEW1, 10), result(1, 30), call(2, NOTES, 20), result(2, 40)]
    assert drift(run(prompts, case=FIRST, events=disagree)) is False  # later line, earlier timestamp
    unmatched = sequential(
        [REVIEW1, "Write notes to outputs/notes.md."]
    )  # saved text differs from the call's
    assert drift(run(prompts, case=FIRST, events=unmatched)) is False
    # the subagent kept working after its result came back (still running): not finished before the notes
    late = [
        call(1, REVIEW1, 10),
        result(1, 11),
        call(2, NOTES, 20),
        {"type": "assistant", "parent_tool_use_id": "t1"},
    ]
    assert drift(run(prompts, case=FIRST, events=late)) is False


def test_only_unnamed_notes_leave_nothing_to_check():
    assert drift(run([NOTES], case=FIRST)) is False  # no reviewer or claim check: nothing shown


def test_transcript_scan_applies_the_same_rule():
    result = run([REVIEW1, NOTES], case=FIRST)
    row = result["results"][1]
    assert row["passed"] is True and row["passed_transcript_scan"] is True, row
    result = run([NOTES, REVIEW1], case=FIRST)
    row = result["results"][1]
    assert row["passed"] is False and row["passed_transcript_scan"] is False, row
