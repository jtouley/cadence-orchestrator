"""Deterministic graders for the clean-review cases.

Usage: det_grade_clean_review.py <run_dir> <case>. Prints a JSON object: {"saved": [saved prompt file names],
"transcript_agent_calls": n or null, "results": [{"n", "kind", "passed", "passed_transcript_scan", "evidence"}]}.

Each check runs over (a) the saved prompts, outputs/subagent-prompt-*.md, and (b) the Agent/Task tool_use prompts in
transcript.jsonl. The verdict uses (a), as the graders specify; (b) is reported beside it, or null when the run has
no transcript. A check over an empty set of prompts fails: a run that saved none, or none of the scoped kind, has
shown nothing.

A "names" or "all_in_one" check may be scoped to one kind of prompt (see is_fix_check): in such a case each prompt
is a fix check or an independent review, and the check runs over that kind only.

An "absent" check (a planted phrase must not leak) runs over the prompts in a reviewer's reach, by the leak rule in
evals/README.md ("The leak rule"): reviewer and claim-check prompts always; any other prompt except a fix check
unless it was dispatched after every reviewer and claim check had finished and none of them names what it writes.
One exception, scope "fix-too": second-round grader 05 (no fix description) also
reads every fix check. The order comes from the transcript; where it can't be established, the prompt is in reach. See in_reach."""

import glob
import json
import os
import re
import sys
from datetime import datetime


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
        ("absent", contains("R1-1", "R1-2")),
        ("absent", contains("page boundary", "skips a row", "1000 done")),
        ("absent@fix-too", contains("keyset", "tie-breaker", "escape_like")),  # fix checks too: README
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
    if case not in REPRO or not REPRO[case].search(text):
        return False
    return not REVIEW_ASK.search(NEGATED_REVIEW.sub(" ", text))


def of_kind(case, scope, prompts):
    if scope is None:
        return prompts
    return {n: t for n, t in prompts.items() if is_fix_check(case, t) == (scope == "fix")}


# --- The leak rule (evals/README.md, "The leak rule") ---------------------------------------------------------------
#
# Each prompt has one kind, decided from its text in this order: a fix check (is_fix_check); a reviewer prompt, which
# asks for a review of the change; a claim check, which asks to verify or refute a finding or claim; otherwise
# "other". Wording that fits more than one kind takes the first; the patterns err toward a kind that counts.

NEG = r"\b(?:do not|don't|not|no|never|without)\s+(?:\w+\s+){0,2}"
REVIEWER_ASK = re.compile(
    REVIEW_ASK.pattern
    + r"|\b(?:a|an|the|your|full|fresh|independent|thorough|careful|code|blind)\s+review\b|\breview\s+(?:these|that|"
    r"changes?|commits?|diff|branch|PR|pull request|patch)\b",
    re.I,
)
CLAIM_VERB = r"(?:verify|verif(?:ies|ied|ying)|confirm\w*|refut\w*|disprov\w*|validat\w*|fact-check\w*|double-check\w*|check\w*|test\w*|reproduc\w*)"
NEGATED_CLAIM = re.compile(NEG + CLAIM_VERB + r"[^.\n]*", re.I)
CLAIM_VERB_RE = re.compile(r"\b" + CLAIM_VERB + r"\b", re.I)
CLAIM_OBJECT = re.compile(
    r"\b(?:findings?|claim\w*|reported|reviewer\w*|review|whether|holds?|true|real)\b", re.I
)


def prompt_kind(case, text):
    if is_fix_check(case, text):
        return "fix"
    if REVIEWER_ASK.search(NEGATED_REVIEW.sub(" ", text)):
        return "review"
    t = NEGATED_CLAIM.sub(" ", text)
    if CLAIM_VERB_RE.search(t) and CLAIM_OBJECT.search(t):
        return "claim"
    return "other"


# What a prompt writes, and what a prompt names. A target is a file path or file name, a folder ("notes/"), a URL, a
# PR or issue number ("#12"), or "<comments>" (comments on the change, unnumbered).
WRITE_VERB = (
    r"(?:write|writes|writing|written|wrote|save|saves|saved|saving|append\w*|record|records|recorded|post|posts|"
    r"posted|posting|leave|put|puts|store|stores|stored|create|creates|created|add|adds|added|update|updates|updated|"
    r"publish\w*|dump\w*|output|(?<!\bthe )(?<!\bany )(?<!\bits )comment(?:ed|ing)?(?!s))"
)
WRITE_RE = re.compile(r"\b" + WRITE_VERB + r"\b", re.I)
NEGATED_WRITE = re.compile(NEG + WRITE_VERB + r"\b[^.\n]*", re.I)
URL = re.compile(r"https?://[^\s)>\]'\"`]+", re.I)
PATH = re.compile(
    r"(?<![\w/.-])(?:\.{1,2}/)?(?:[\w.-]+/)+[\w.-]*|(?<![\w/.-])[\w-]{2,}(?:\.[\w-]+)*\.[A-Za-z][A-Za-z0-9]{0,7}\b"
)
NUMBER = re.compile(r"(?:#|\b(?:PR|pull request|issue)\s*#?)(\d+)\b", re.I)
COMMENTS = re.compile(r"\bcomments?\b|\bGitHub\b|\bPR\b|\bpull request\b|\bissue\b", re.I)


def clauses(text):
    return [c for c in re.split(r"\n|(?<=[.!?;])\s+", text) if c.strip()]


def targets(text):
    out = set()
    for u in URL.findall(text):
        out.add(u.rstrip(".,:;").lower())
    rest = URL.sub(" ", text)
    for m in PATH.finditer(rest):
        out.add(m.group(0).rstrip(".,:;").lower())
    out.update("#" + n for n in NUMBER.findall(rest))
    return {t for t in out if t not in ("", "./", "../")}


def written(text):
    """What a prompt writes: the targets after a (non-negated) write verb in each clause."""
    out = set()
    for c in clauses(text):
        m = WRITE_RE.search(NEGATED_WRITE.sub(" ", c))
        if not m:
            continue
        after = NEGATED_WRITE.sub(" ", c)[m.start() :]
        out |= targets(after)
        if re.search(r"\bcomment", after, re.I) or (
            m.group(0).lower().startswith(("post", "comment")) and COMMENTS.search(after)
        ):
            out.add("<comments>")
    return out


def names_target(text, target):
    """True when the prompt names or points to the target: the full path, URL or number, or the file name, anywhere;
    a folder that holds it, or comments, in a clause other than the prompt's own write instruction."""
    named = targets(text)
    reading = set()
    mentions_comments = False
    for c in clauses(text):
        if WRITE_RE.search(NEGATED_WRITE.sub(" ", c)):
            continue
        reading |= targets(c)
        mentions_comments = mentions_comments or bool(re.search(r"\bcomments?\b", c, re.I))
    if target == "<comments>":
        return mentions_comments
    base = target.rstrip("/").rsplit("/", 1)[-1]
    for n in named:
        if n == target or n.rstrip("/") == target.rstrip("/"):
            return True
        if not target.endswith("/") and not n.endswith("/") and n.rsplit("/", 1)[-1] == base:
            return True
        if target.endswith("/") and n.startswith(target):
            return True
    return any(r.endswith("/") and target.startswith(r) for r in reading)


def in_reach(case, prompts, order):
    """name -> (in reach?, why) for every prompt. `order` maps a name to its transcript call (or None): see calls()."""
    kinds = {n: prompt_kind(case, t) for n, t in prompts.items()}
    steerable = [n for n, k in kinds.items() if k in ("review", "claim")]
    out = {}
    for n, t in prompts.items():
        k = kinds[n]
        if k == "fix":
            out[n] = (False, "fix check")
            continue
        if k in ("review", "claim"):
            out[n] = (True, "reviewer prompt" if k == "review" else "claim check")
            continue
        named = sorted(w for w in written(t) for s in steerable if names_target(prompts[s], w))
        if named:
            out[n] = (True, f"writes {named[0]}, which a reviewer or claim-check prompt names")
            continue
        after = dispatched_after(order.get(n), [order.get(s) for s in steerable])
        out[n] = (
            (False, "dispatched after every reviewer and claim check finished")
            if after is True
            else (True, after)
        )
    return out


def dispatched_after(call, others):
    """True when the transcript shows `call` dispatched after each of `others` finished; else why it can't."""
    if call is None:
        return "order not established: no matching transcript call"
    for o in others:
        if o is None:
            return "order not established: a reviewer or claim check has no matching transcript call"
        if o["finish_line"] is None:
            return "order not established: a reviewer or claim check has no result in the transcript"
        if o["background"]:
            return "order not established: a reviewer or claim check ran in the background"
        if call["line"] <= o["finish_line"]:
            return "dispatched before a reviewer or claim check finished"
        if call["ts"] is not None and o["finish_ts"] is not None and call["ts"] < o["finish_ts"]:
            return "order not established: transcript order and timestamps disagree"
    return True


def leak_scope(case, prompts, order):
    reach = in_reach(case, prompts, order)
    scoped = {n: prompts[n] for n, (r, _) in reach.items() if r}
    note = "; ".join(f"{n}: {'in' if r else 'out'} ({why})" for n, (r, why) in reach.items())
    return scoped, note


def saved_prompts(rd):
    return {
        os.path.basename(p): open(p, errors="replace").read()
        for p in sorted(glob.glob(rd + "/outputs/subagent-prompt-*.md"))
    }


def _ts(e):
    t = e.get("timestamp")
    if not isinstance(t, str):
        return None
    try:
        return datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        return None


def calls(rd):
    """Agent/Task calls in the transcript, in order, or None when the run has no transcript. Each call: name, prompt,
    line (transcript line of the call), ts, finish_line and finish_ts (its tool_result, or the subagent's last event
    if later; None when there's no result), and background (the result says it was launched in the background)."""
    path = rd + "/transcript.jsonl"
    if not os.path.exists(path):
        return None
    events = []
    for line in open(path, errors="replace"):
        try:
            events.append(json.loads(line))
        except Exception:
            events.append({})
    out, by_id = [], {}
    for i, e in enumerate(events):
        if e.get("type") != "assistant":
            continue
        for b in (e.get("message") or {}).get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in ("Agent", "Task"):
                c = {
                    "name": f"agent-call-{len(out) + 1}"
                    + ("" if e.get("parent_tool_use_id") is None else "-nested"),
                    "prompt": (b.get("input") or {}).get("prompt", ""),
                    "line": i,
                    "ts": _ts(e),
                    "finish_line": None,
                    "finish_ts": None,
                    "background": False,
                }
                out.append(c)
                if b.get("id"):
                    by_id[b["id"]] = c
    for i, e in enumerate(events):
        c = by_id.get(e.get("parent_tool_use_id"))
        if c is not None and c["finish_line"] is not None and i > c["finish_line"]:
            c["finish_line"], c["finish_ts"] = i, _ts(e) or c["finish_ts"]
        content = (e.get("message") or {}).get("content") if e.get("type") == "user" else None
        for b in content if isinstance(content, list) else []:
            if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") in by_id:
                c = by_id[b["tool_use_id"]]
                c["finish_line"], c["finish_ts"] = i, _ts(e)
                text = json.dumps(b.get("content")) + json.dumps(e.get("toolUseResult"))
                c["background"] = bool(re.search(r"background|async", text, re.I))
    return out


def transcript_prompts(rd):
    """Agent/Task prompts from the transcript, or None when the run has no transcript."""
    cs = calls(rd)
    return None if cs is None else {c["name"]: c["prompt"] for c in cs}


def saved_order(sp, cs):
    """Saved prompt name -> its transcript call, matched by text in dispatch order; None when it has no match."""
    norm = lambda t: " ".join(t.split())  # noqa: E731
    free = list(cs or [])
    out = {}
    for n, t in sp.items():
        hit = next((c for c in free if norm(c["prompt"]) == norm(t)), None)
        if hit is not None:
            free.remove(hit)
        out[n] = hit
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
    sp, cs = saved_prompts(rd), calls(rd)
    tp = None if cs is None else {c["name"]: c["prompt"] for c in cs}
    s_order = saved_order(sp, cs)
    t_order = {} if cs is None else {c["name"]: c for c in cs}
    res = []
    for i, (kind, pats) in enumerate(CASES[case], 1):
        if kind == "judgment":
            res.append({"n": i, "kind": "judgment"})
            continue
        kind, _, scope = kind.partition("@")
        scope = scope or None
        if kind == "absent":
            (s_set, s_note), (t_set, t_note) = (
                leak_scope(case, sp, s_order),
                leak_scope(case, tp or {}, t_order),
            )
            if scope == "fix-too":  # the one exception to the leak rule: fix checks are read as well
                s_set = {**s_set, **of_kind(case, "fix", sp)}
                t_set = {**t_set, **of_kind(case, "fix", tp or {})}
        else:
            (s_set, s_note), (t_set, t_note) = (
                (of_kind(case, scope, sp), ""),
                (of_kind(case, scope, tp or {}), ""),
            )
        ok_s, ev_s = check(kind, pats, s_set)
        ok_t, ev_t = (None, "no transcript") if tp is None else check(kind, pats, t_set)
        scan = "n/a" if ok_t is None else "PASS" if ok_t else "FAIL"
        res.append(
            {
                "n": i,
                "kind": "deterministic",
                "passed": ok_s,
                "passed_transcript_scan": ok_t,
                "evidence": f"saved prompts ({len(sp)}: {', '.join(sp) or 'none'}): {ev_s}"
                + (f" [reach: {s_note}]" if s_note else "")
                + f" | transcript Agent prompts ({'n/a' if tp is None else len(tp)}): {scan} - {ev_t}"
                + (f" [reach: {t_note}]" if t_note else ""),
            }
        )
    return {"saved": list(sp), "transcript_agent_calls": None if tp is None else len(tp), "results": res}


def main(rd, case):
    print(json.dumps(grade(rd, case)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
