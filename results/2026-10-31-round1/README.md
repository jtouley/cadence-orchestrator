# Round 1, 2026-10-31: exploratory baseline (not a ship decision)

A copy of coffee-data-tracker `.claude/skills/tpm-workspace/iteration-1/`: transcripts, run outputs, `benchmark.json/md`, and `grading.json` and `script_checks.json` per run. That workspace is git-excluded
there, so this copy and its checksums are the record. `scripts/` holds the round's `grade_checks.py`, which
extracted the facts, and `write_grading_iter1.py`, which holds the verdicts. `scorer_output.txt` is
`evals/scripts/score.py` (eval-setup branch) run over this folder.

Why it's exploratory: 3 cases, all against coffee-data-tracker, with unrecorded authors (tainted-unknown). n=1 run
per arm. Arms are `with_skill` vs `without_skill`, not main vs a change. Each run was graded once by one grader
(Claude Opus 5.5), mixing script facts and judgment, with no second labeler or tie-break and no blinding to arm.
The `build-finish-bag-screen/with_skill` run was cut off by the harness before review (see `benchmark.md`).

Integrity: `SHA256SUMS` covers every file under `results/` except itself. `sha256sum -c SHA256SUMS` from `results/`.

**Prepared for publishing (2026-10-31).** The `session_log/` directories, the raw per-session logs including
subagent logs, were removed before publishing. Every `transcript.jsonl`, run output and grading file is kept. Email
addresses were replaced with `<redacted>` where they appeared: the `Co-Authored-By` trailer address in commit
messages and briefs, in `tempting-quick-ratio-fix/with_skill/{transcript.jsonl, outputs/02-brief-investigate.md}`. Redacted JSONL lines were re-serialized from their parsed values, and the JSON
stays valid. No other user identifiers or credentials were found (see the scan in the commit message). These files
therefore no longer match the source workspace byte for byte. `SHA256SUMS` covers the published files.
