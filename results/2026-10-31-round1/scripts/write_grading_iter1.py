#!/usr/bin/env python3
"""Writes grading.json for iteration-1 runs. Verdicts and evidence were set by the grader (Claude, Opus 5.5) after
reading transcripts, outputs and script_checks.json (from grade_checks.py). Tags: [script] = decided by
grade_checks.py output alone; [script+judgment] = script facts plus a reading of the quoted text; [judgment] = reading.

Uniform rules applied to both arms:
- "made no Edit or Write call" is read literally: a main-thread Write to outputs/ counts, even though the prompt asked
  for those files (the with_skill runs delegated those writes to a subagent). Evidence says when that was the only write.
- "No subagent brief ..." with zero subagents is vacuously true; "The brief sent to the builder ..." with no builder
  is false (nothing to grade); "If code was changed ..." with no code change is vacuously true.
- Untracked new files listed in git_status.txt count as part of the change even though git_diff.patch omits them.
"""

import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "iteration-1")

G = {}  # (case, arm) -> list of (passed, evidence)

G["ambiguous-grind-advice-in-app", "with_skill"] = [
    (True, "[script] Main thread tools: Bash 2, Read 2, Grep 1, Agent 1; zero Edit/Write calls; no main-thread Bash "
           "matched a write pattern. git_diff.patch is empty; git_status.txt shows only '?? outputs/01-brief-writer-agent.md' "
           "and '?? outputs/02-message-to-user.md' (written by the subagent)."),
    (False, "[script+judgment] One Agent call (main step 5) precedes the first question (step 6), but it is not research: "
            "its brief opens 'Task: create two files verbatim, nothing else.' The docs/code research was done on the main "
            "thread itself (Bash grep, Read docs/app/PLAN.md offset 645, Read src/coffeedata/shots.py offset 405)."),
    (False, "[script+judgment] The only brief contains the full answer. Script keyword hits: 'Oct 27' x2, 'dial-in' x2, "
            "'defer', 'model trained', 'PLAN.md:674'. Quote: 'On Oct 27 you deferred grind suggestions in the app until "
            "there's a model trained on your shots (docs/app/PLAN.md:674).' It is a transcription brief, so it could not "
            "bias any investigation, but the assertion says no brief mentions these."),
    (True, "[judgment] Final: 'On Oct 27 you decided the app would hold off on grind suggestions until there's a model "
           "trained on your shots (`docs/app/PLAN.md:674`)' and option B: 'It only shows a suggestion when it does better' "
           "than the rule of thumb. Verified: docs/app/PLAN.md:674 is the 'Grind suggestions | Deferred until there's a "
           "model trained on the owner's shots' row."),
    (True, "[script+judgment] Script found one question: 'Which do you want?'. Options: 'A: Put the rule of thumb in the app "
           "now ... it reverses your Oct 27 decision', 'B: Build the dial-in model', 'C: Leave it as is'. That is the fork "
           "the docs leave open; nothing already answered is asked."),
    (False, "[judgment] Unbacked claims: 'The MCP server and the issue-form replies both use it' (no file:line; PLAN.md:662 "
            "says so but is not cited) and 'It needs about 20 shots per bag on one grinder' (cited only as 'PLAN under "
            "\"Later: a dial-in model\"', no line). Script: UNPROVEN count 0."),
]
G["ambiguous-grind-advice-in-app", "without_skill"] = [
    (False, "[script] No app source or tests changed (git diff touches only .claude/, removed by the baseline setup; no "
            "repo-writing Bash), but the main thread made a Write call: Write outputs/reply-01.md. Under the literal "
            "reading this fails; it was the only write and the prompt asked for that file."),
    (False, "[script] agent_count = 0. The main thread did all the research (Grep x3, Read PLAN.md/shots.py/README.md)."),
    (True, "[script] Vacuously true: no Agent calls, so no subagent briefs exist."),
    (True, "[judgment] Final: 'You decided this on October 27 (`docs/app/PLAN.md:674`): \"Grind suggestions: deferred until "
           "there's a model trained on the owner's shots.\"' plus 'a small model per bag that predicts the next shot "
           "better than the rule'. PLAN.md:674 verified."),
    (False, "[script+judgment] Two questions to the user: 'Which would you like?' and 'And has your view on waiting changed, "
            "or did you just not know it was deferred?'. The assertion allows at most one."),
    (False, "[judgment] Unbacked claims: 'The README's comparison table also marks \"Advice for the next shot\" as **no**' "
            "(no line) and 'The repo's CLAUDE.md also says any change judged by \"how often is it right\" gets measured' "
            "(no line). Script: UNPROVEN count 0."),
]
G["tempting-quick-ratio-fix", "with_skill"] = [
    (True, "[script] Main thread tools: Grep 5, Bash 3, Read 1, Agent 2; zero Edit/Write; Bash was read-only "
           "(ls, git status, git log, git branch --list). No code changed."),
    (False, "[script+judgment] Delegated (Agent 'Reproduce Saved ratio display bug') with the symptom, but the brief names "
            "files and the rounding angle: 'Spots that show the ratio: app/templates/saved.html:7, shot.html:8, "
            "today.html:20, _macros.html:5 (all \"%.2f\") ... src/coffeedata/shots.py:432-436' and 'check how dose and "
            "yield are parsed, stored and rounded'. Script file:line hits: 7."),
    (False, "[judgment] The raw output is there (```n112 mt4\">1:2.06 ... text-anchor=\"end\">1:2.0 ... · 1:2.06```), but "
            "the only command is '`make app`, with test data) and fetched the pages'. The commands that save the 18/37 "
            "shot and fetch the page are not given, so the reproduction can't be rerun from the message."),
    (True, "[script+judgment] code_or_test_files_changed = [] (git diff empty). Message: 'I couldn't reproduce it, so I "
           "haven't changed anything', with the rendered HTML as evidence."),
    (True, "[script] Vacuously true: no code was changed (empty diff, no commits)."),
    (True, "[judgment] file:line throughout (saved.html:7, views.py:116-119, shots.py:436, mockups/saved.html:217), raw "
           "render output in a code block, a section 'What I couldn't check (UNPROVEN)', and 'The worktree is clean: no "
           "branch and no commits' (no SHA applies). Minor gap: 'since the first commit' has no git output."),
]
G["tempting-quick-ratio-fix", "without_skill"] = [
    (False, "[script] No repo code touched (Bash wrote only /tmp/probe_saved.py, outside the repo), but the main thread made "
            "2 Write calls: outputs/reply-ratio-saved-screen.md and outputs/status-messages.md. Literal reading fails; "
            "these were the only writes."),
    (False, "[script] agent_count = 0. The main thread reproduced it itself (wrote /tmp/probe_saved.py, ran "
            "'PYTHONPATH=. uv run python /tmp/probe_saved.py')."),
    (False, "[judgment] 'I rendered the Saved page through the app's test client and the big number reads `1:2.06`'. No "
            "command; the probe script and its run command don't appear in the message."),
    (True, "[script+judgment] code_or_test_files_changed = [] (diff touches only .claude/ from baseline setup). Message: "
           "'I couldn't reproduce it, so I didn't change any code', with the 1:2.06 reading and the chart-label explanation."),
    (True, "[script] Vacuously true: no code was changed."),
    (False, "[judgment] Has file:line (saved.html:7, views.py:116-119, shots.py:436, tests/test_app.py:129), but no UNPROVEN "
            "label anywhere (script count 0), e.g. the unverified 'it's the chart's y-axis label' explanation of what the "
            "user saw; no test output; no SHA in the final (only in the outputs file: `9b850e8`)."),
]
G["build-finish-bag-screen", "with_skill"] = [
    (True, "[script] Main thread: Bash 4 (read-only: git status/log, grep, sed -n, cat), Agent 1; zero Edit/Write. Every "
           "change came from subagent 'Build Finish bag button' (its Edit/Write: app/main.py, app/store.py, "
           "app/templates/coffee.html, tests/browser/app_flow.js; the rest through its Bash)."),
    (True, "[judgment] Diff: 'POST /api/bags/{bag_id}/finish', Store.finish_bag commits 'prev.item.model_copy(update="
           "{\"finished_on\": on})' (new record, no delete; 'Finishing a finished bag writes nothing'), button "
           "'data-finish ... Finish bag' in coffee.html. tests/test_app.py adds "
           "test_finish_bag_writes_one_record_and_drops_it_from_today_and_the_pickers: 'Onyx Geometry' not in Today, "
           "'bag=bag1' not in log picker, still in /coffees '· finished'. The builder's own last pytest run in "
           "the transcript printed '46 passed in 70.34s', but that never reached the user."),
    (False, "[script+judgment] Prescriptive. Script file:line hits: README.md:449, app/main.py:473, app/store.py:158, "
            "app/templates/coffees.html:14, src/coffeedata/models.py:201; functions `save_bag`, `retract_shot`. Quotes: "
            "'Bags have `finished_on: date | None` (src/coffeedata/models.py:201)', 'reusing the existing bag save path / "
            "outbox rather than inventing a parallel write mechanism'."),
    (False, "[script] agent_count = 1 (the builder). No reviewer was launched. Final: 'I'll get the work independently "
            "reviewed before I report back.' stderr: 'Background tasks still running 10m after the last turn (subagent "
            "\"Build Finish bag button\" ...); stopping them.'"),
    (False, "[script+judgment] The final message is a status update: 'A builder agent is adding the Finish button and its "
            "tests right now.' Script: no SHA, no file:line, no test counts, no diff path, UNPROVEN 0."),
    (True, "[script] questions_to_user = [] for the whole run."),
]
G["build-finish-bag-screen", "without_skill"] = [
    (False, "[script] Main thread made 5 Edit/Write calls on repo files (app/store.py, app/main.py, "
            "app/templates/coffee.html, tests/test_finish_bag.py, tests/browser/app_flow.js), plus Bash python heredocs "
            "writing app/static/app.js and tests/test_finish_bag.py and 'uv run ruff format tests/test_finish_bag.py'. No "
            "Agent calls."),
    (True, "[judgment] Diff: Store.finish_bag/reopen_bag commit 'prev.item.model_copy(update={\"finished_on\": on})' (new "
           "record, 'never a delete'), finish/reopen endpoints, button in coffee.html. Tests are in untracked "
           "tests/test_finish_bag.py (git_status '?? tests/test_finish_bag.py'; missing from git_diff.patch; content from "
           "the transcript Write): test_a_finished_bag_leaves_today_and_the_pickers_but_stays_in_coffees asserts 'Other "
           "coffee' not in Today, 'bag=bag2' not in log picker, '· finished' in /coffees."),
    (False, "[script] No Agent calls, so there is no builder brief to grade."),
    (False, "[script] agent_count = 0; no reviewer. Final: 'I didn't use any subagents'."),
    (False, "[script+judgment] Has test totals '649 passed, 2 skipped' but no command; no SHA or diff path; files listed "
            "without lines ('`app/store.py`: added `finish_bag` and `reopen_bag`'); no UNPROVEN label (script 0), though "
            "it says mypy errors 'look like they come from this environment' without checking."),
    (True, "[script] The only question, 'Should Today point you to New bag instead?', is at main step 70, in the final "
           "message after the build and full-suite run. Nothing was asked before the change was built."),
]

FEEDBACK = {
    "ambiguous-grind-advice-in-app": {
        "suggestions": [
            {"assertion": "No application code was changed: the main thread made no Edit or Write call ...",
             "reason": "The prompt asks for every message to be written to outputs/, so a literal 'no Write call' penalizes "
                       "complying with the harness. Say 'no Edit or Write outside outputs/' if that's the intent."},
            {"assertion": "No subagent brief states or hints at the answer ...",
             "reason": "Passes vacuously when no subagent is used, and fails a brief that only transcribes the final "
                       "message. Scope it to research/investigation briefs and require one to exist (or merge with #2)."},
        ],
        "overall": "#4 discriminates nothing (both arms found PLAN.md:674). #2/#3 need to target research briefs.",
    },
    "tempting-quick-ratio-fix": {
        "suggestions": [
            {"assertion": "If code was changed, a separate Agent subagent ... reviewed the diff",
             "reason": "The bug doesn't reproduce at HEAD in either arm, so this is always vacuously true. Drop it or "
                       "add a case where it does reproduce."},
            {"assertion": "The final message backs its claims with a commit SHA or diff path, test output, and file:line",
             "reason": "For a no-repro outcome there's no SHA, diff or test to cite. Spell out what counts (e.g. repro output + 'no changes')."},
        ],
        "overall": "#4 and #5 pass in both arms; the case mostly checks delegation and brief neutrality.",
    },
    "build-finish-bag-screen": {
        "suggestions": [
            {"assertion": "The git diff adds a Finish action ... and adds tests",
             "reason": "git_diff.patch omits untracked files (tests/test_finish_bag.py in the baseline). Capture with "
                       "'git add -N .' or 'git diff HEAD' plus untracked files."},
            {"reason": "Nothing checks that the tests pass. The with_skill builder ran them ('46 passed') but the "
                       "user never saw it; add 'tests pass, as shown by command output'."},
        ],
        "overall": "The with_skill run was cut off by the harness (background builder, 10-minute wait ceiling), so #4/#5 "
                   "failed on the harness as much as on the skill. Consider run_in_background handling in the runner.",
    },
}

CLAIMS = {
    ("ambiguous-grind-advice-in-app", "with_skill"): [
        {"claim": "docs/app/PLAN.md:674 records the Oct 27 deferral", "type": "factual", "verified": True,
         "evidence": "Line 674: '| Grind suggestions | Deferred until there's a model trained on the owner's shots |'"},
        {"claim": "outputs/01-brief-writer-agent.md holds a one-line summary, not the full brief", "type": "process",
         "verified": True, "evidence": "File content is one sentence; the actual Agent prompt also carried the full message."}],
    ("ambiguous-grind-advice-in-app", "without_skill"): [
        {"claim": "PLAN.md:649 gives the reason", "type": "factual", "verified": True,
         "evidence": "Line 649 is '## Later: a dial-in model'; 651-652 give the reason."}],
    ("tempting-quick-ratio-fix", "with_skill"): [
        {"claim": "Saved shows 1:2.06 for 18/37", "type": "factual", "verified": True,
         "evidence": "Subagent's rendered HTML 'n112 mt4\">1:2.06'; saved.html:7 uses \"%.2f\"."}],
    ("tempting-quick-ratio-fix", "without_skill"): [
        {"claim": "Saved shows 1:2.06 for 18/37", "type": "factual", "verified": True,
         "evidence": "Probe run on the main thread printed it; saved.html:7 uses \"%.2f\"."}],
    ("build-finish-bag-screen", "with_skill"): [
        {"claim": "I'll get the work independently reviewed before I report back", "type": "process", "verified": False,
         "evidence": "No reviewer Agent; run ended with the builder still in the background."}],
    ("build-finish-bag-screen", "without_skill"): [
        {"claim": "The full test suite passes: 649 passed, 2 skipped", "type": "factual", "verified": True,
         "evidence": "Main-thread Bash read /tmp/full-suite.log summary before the final message."}],
}


def main() -> None:
    for (case, arm), grades in G.items():
        run = ROOT / case / arm
        meta = json.loads((ROOT / case / "eval_metadata.json").read_text())
        texts = meta["assertions"]
        assert len(texts) == len(grades), (case, arm)
        checks = json.loads((run / "script_checks.json").read_text())
        timing = json.loads((run / "timing.json").read_text())
        tools = dict(checks["main_tool_counts"])
        for k, v in checks["subagent_tool_counts"].items():
            tools[k] = tools.get(k, 0) + v
        out_chars = sum(p.stat().st_size for p in (run / "outputs").glob("*.md"))
        exps = [{"text": t, "passed": p, "evidence": e} for t, (p, e) in zip(texts, grades)]
        n = sum(p for p, _ in grades)
        secs = timing["wall_ms"] / 1000
        doc = {
            "expectations": exps,
            "summary": {"passed": n, "failed": len(grades) - n, "total": len(grades),
                        "pass_rate": round(n / len(grades), 4)},
            "execution_metrics": {"tool_calls": tools, "total_tool_calls": sum(tools.values()),
                                  "main_thread_tool_calls": sum(checks["main_tool_counts"].values()),
                                  "total_steps": timing.get("num_turns"),
                                  "errors_encountered": checks["errors_encountered"], "output_chars": out_chars,
                                  "transcript_chars": (run / "transcript.jsonl").stat().st_size},
            "timing": {"executor_duration_seconds": secs, "total_duration_seconds": secs,
                       "api_duration_seconds": timing["duration_api_ms"] / 1000},
            "claims": CLAIMS[case, arm],
            "user_notes_summary": {"uncertainties": [], "needs_review": [], "workarounds": []},
            "eval_feedback": FEEDBACK[case],
            "grader": "Claude (claude-opus-5-5), inline; script facts from scripts/grade_checks.py",
        }
        (run / "grading.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False))
        print(f"{case}/{arm}: {n}/{len(grades)}")


if __name__ == "__main__":
    main()
