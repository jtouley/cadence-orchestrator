"""Deterministic graders for the clean-review cases.

Usage: det_grade_clean_review.py <run_dir> <case>. Prints a JSON object: {"saved": [saved prompt file names],
"transcript_agent_calls": n or null, "results": [{"n", "kind", "passed", "passed_transcript_scan", "evidence"}]}.

Each check runs over (a) the saved prompts, outputs/subagent-prompt-*.md, and (b) the Agent/Task tool_use prompts in
transcript.jsonl. The verdict uses (a), as the graders specify; (b) is reported beside it, or null when the run has
no transcript. A check over an empty set of prompts fails: a run that saved none, or none of the scoped kind, has
shown nothing.

A check may be scoped to one kind of prompt (see is_fix_check): in such a case each prompt is a fix check or an
independent review, and the check runs over that kind only."""

import glob
import json
import os
import re
import sys


def rng(base, head):
    return re.compile(rf"(?:{base})\.\.\.?(?:{head})", re.I)


def both_names(base_word, head_name):
    # both branch names given as base and head, e.g. "base: main ... head: feature/x" or "feature/x against main"
    return re.compile(
        rf"(?:\bbase\b[^\n]{{0,40}}\b{base_word}\b[\s\S]{{0,200}}{head_name})|(?:{head_name}[^\n]{{0,60}}\b(?:against|onto|into|relative to|compared (?:to|with)|vs\.?|versus)\s+`?(?:origin/)?{base_word}\b)|(?:\bfrom\s+`?(?:origin/)?{base_word}`?\s+to\s+`?{head_name})",
        re.I,
    )


def contains(*phrases):
    return [re.compile(re.escape(p), re.I) for p in phrases]


CASES = {
    "first-review-hides-suspected-bug": [
        (
            "names",
            [
                rng(
                    r"(?:origin/)?main|f7f6429[0-9a-f]*", r"(?:origin/)?feature/token-bucket|3050047[0-9a-f]*"
                ),
                both_names("main", r"feature/token-bucket"),
            ],
        ),
        ("absent", contains("clock drifts")),
        ("absent", contains("across the sleep", "lock is held")),
        ("absent", contains("priya")),
        ("judgment", None),
    ],
    "second-round-hides-prior-findings": [
        (
            "names@review",
            [
                rng(
                    r"(?:origin/)?main|6a70bbd[0-9a-f]*",
                    r"(?:origin/)?feature/search-api|round-2|6746708[0-9a-f]*",
                ),
                rng(r"round-1|87fe0d8[0-9a-f]*", r"round-2|6746708[0-9a-f]*"),
                both_names("main", r"feature/search-api"),
            ],
        ),
        (
            "all_in_one@fix",
            [
                contains("R1-1", "skips a row on every page boundary", "r1_1_cursor_gap.py"),
                contains("R1-2", "LIKE wildcards in the search term", "r1_2_like_wildcard.py"),
            ],
        ),
        ("absent@review", contains("R1-1", "R1-2")),
        ("absent@review", contains("page boundary", "skips a row", "1000 done")),
        ("absent", contains("keyset", "tie-breaker", "escape_like")),
        ("judgment", None),
    ],
    "spec-review-hides-weak-spots": [
        ("names", [re.compile(r"rfc\s?9457|https://www\.rfc-editor\.org/rfc/rfc9457", re.I)]),
        (
            "names",
            [
                rng(
                    r"(?:origin/)?main|7ae6e38[0-9a-f]*",
                    r"(?:origin/)?feature/problem-details|5efb782[0-9a-f]*",
                ),
                both_names("main", r"feature/problem-details"),
            ],
        ),
        ("absent", contains("weak spot", "stringif")),
        ("absent", contains("double-encod", "double encod")),
        ("absent", contains("hunch", "I have a feeling", "not convinced")),
        ("judgment", None),
    ],
}


# Cases whose prompts come in two kinds. A fix check names a repro script and doesn't ask for a review of the
# change; every other prompt, including one that combines both, is an independent review.
REPRO = {
    "second-round-hides-prior-findings": re.compile(r"r1_1_cursor_gap\.py|r1_2_like_wildcard\.py", re.I),
}
# Asking for a review: the review skill, "review the/this/of/...", or a commit range. Negated asks ("don't review
# the branch") are removed first.
NEGATED_REVIEW = re.compile(
    r"\b(?:do not|don't|not|no|never|without)\s+(?:\w+\s+){0,2}review\w*[^.\n]*", re.I
)
REVIEW_ASK = re.compile(
    r"/code-review|\breview(?:ing)?\s+(?:the|this|of|main|origin/|feature/|round-|all|it)\b|\b\w[\w/-]*\.\.\.?\w[\w/-]*",
    re.I,
)


def is_fix_check(case, text):
    if not REPRO[case].search(text):
        return False
    return not REVIEW_ASK.search(NEGATED_REVIEW.sub(" ", text))


def of_kind(case, scope, prompts):
    if scope is None:
        return prompts
    return {n: t for n, t in prompts.items() if is_fix_check(case, t) == (scope == "fix")}


def saved_prompts(rd):
    return {
        os.path.basename(p): open(p, errors="replace").read()
        for p in sorted(glob.glob(rd + "/outputs/subagent-prompt-*.md"))
    }


def transcript_prompts(rd):
    """Agent/Task prompts from the transcript, or None when the run has no transcript."""
    path = rd + "/transcript.jsonl"
    if not os.path.exists(path):
        return None
    out = {}
    for line in open(path, errors="replace"):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("type") != "assistant":
            continue
        for b in (e.get("message") or {}).get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in ("Agent", "Task"):
                out[
                    f"agent-call-{len(out) + 1}" + ("" if e.get("parent_tool_use_id") is None else "-nested")
                ] = (b.get("input") or {}).get("prompt", "")
    return out


def check(kind, pats, prompts):
    if not prompts:
        return False, "no prompts of this kind"
    if kind == "all_in_one":
        # each group of phrases must all appear together in a single prompt
        miss = []
        for group in pats:
            names = [n for n, t in prompts.items() if all(p.search(t) for p in group)]
            if not names:
                miss.append(" + ".join(repr(p.pattern.replace("\\", "")) for p in group))
        return not miss, ("each group found" if not miss else "missing: " + "; ".join(miss))
    if kind == "names":
        hits = [(n, p.search(t).group(0)) for n, t in prompts.items() for p in pats if p.search(t)]
        return bool(hits), (f"match {hits[0][1]!r} in {hits[0][0]}" if hits else "no accepted form found")
    hits = [
        (n, p.pattern.replace("\\", ""), t[max(0, m.start() - 60) : m.end() + 60].replace("\n", " "))
        for n, t in prompts.items()
        for p in pats
        for m in [p.search(t)]
        if m
    ]
    return (not hits), (
        "none of the phrases present"
        if not hits
        else "; ".join(f"{h[1]!r} in {h[0]}: …{h[2]}…" for h in hits[:3])
    )


def grade(rd, case):
    sp, tp = saved_prompts(rd), transcript_prompts(rd)
    res = []
    for i, (kind, pats) in enumerate(CASES[case], 1):
        if kind == "judgment":
            res.append({"n": i, "kind": "judgment"})
            continue
        kind, _, scope = kind.partition("@")
        scope = scope or None
        ok_s, ev_s = check(kind, pats, of_kind(case, scope, sp))
        ok_t, ev_t = (None, "no transcript") if tp is None else check(kind, pats, of_kind(case, scope, tp))
        scan = "n/a" if ok_t is None else "PASS" if ok_t else "FAIL"
        res.append(
            {
                "n": i,
                "kind": "deterministic",
                "passed": ok_s,
                "passed_transcript_scan": ok_t,
                "evidence": f"saved prompts ({len(sp)}: {', '.join(sp) or 'none'}): {ev_s} | transcript Agent prompts "
                f"({'n/a' if tp is None else len(tp)}): {scan} - {ev_t}",
            }
        )
    return {"saved": list(sp), "transcript_agent_calls": None if tp is None else len(tp), "results": res}


def main(rd, case):
    print(json.dumps(grade(rd, case)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
