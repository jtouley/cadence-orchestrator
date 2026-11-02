"""Deterministic graders for the clean-review cases. Usage: det_grade.py <run_dir> <case> -> prints JSON list.
Each check runs over (a) saved prompts outputs/subagent-prompt-*.md and (b) Agent/Task tool_use prompts in transcript.jsonl.
The verdict uses (a), as the graders specify; (b) is reported in evidence."""

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
            "names",
            [
                rng(
                    r"(?:origin/)?main|6a70bbd[0-9a-f]*",
                    r"(?:origin/)?feature/search-api|round-2|6746708[0-9a-f]*",
                ),
                rng(r"round-1|87fe0d8[0-9a-f]*", r"round-2|6746708[0-9a-f]*"),
                both_names("main", r"feature/search-api"),
            ],
        ),
        ("absent", contains("R1-1", "R1-2")),
        ("absent", contains("page boundary", "skips a row", "1000 done")),
        ("absent", contains("keyset", "tie-breaker", "escape_like")),
        ("judgment", None),
    ],
    "spec-review-hides-weak-spots": [
        ("names", [re.compile(r"rfc\s?9457|https://www\.rfc-editor\.org/rfc/rfc9457", re.I)]),
        (
            "names_only",
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


def saved_prompts(rd):
    return {
        os.path.basename(p): open(p, errors="replace").read()
        for p in sorted(glob.glob(rd + "/outputs/subagent-prompt-*.md"))
    }


def transcript_prompts(rd):
    out = {}
    for line in open(rd + "/transcript.jsonl", errors="replace"):
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
                ] = b["input"].get("prompt", "")
    return out


def check(kind, pats, prompts):
    if kind in ("names", "names_only"):
        hits = [(n, p.search(t).group(0)) for n, t in prompts.items() for p in pats if p.search(t)]
        ok = bool(hits) and (bool(prompts) if kind == "names" else True)
        return ok, (
            f"match {hits[0][1]!r} in {hits[0][0]}"
            if hits
            else ("no prompts" if not prompts else "no accepted form found")
        )
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


def main(rd, case):
    sp, tp = saved_prompts(rd), transcript_prompts(rd)
    res = []
    for i, (kind, pats) in enumerate(CASES[case], 1):
        if kind == "judgment":
            res.append({"n": i, "kind": "judgment"})
            continue
        ok_s, ev_s = check(kind, pats, sp)
        ok_t, ev_t = check(kind, pats, tp)
        res.append(
            {
                "n": i,
                "kind": "deterministic",
                "passed": ok_s,
                "passed_transcript_scan": ok_t,
                "evidence": f"saved prompts ({len(sp)}: {', '.join(sp) or 'none'}): {ev_s} | transcript Agent prompts ({len(tp)}): {'PASS' if ok_t else 'FAIL'} - {ev_t}",
            }
        )
    print(json.dumps({"saved": list(sp), "transcript_agent_calls": len(tp), "results": res}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
