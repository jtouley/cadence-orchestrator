# Evaluating the tpm skill

This folder defines how the skill is measured: the cases, the labeling guide for judgment assertions, the
deterministic scorer and the floors. Run results live on the `orchestration` branch (see Results). The procedure
follows coffee-data-tracker's "Heuristics and models are measured, not argued" (its CLAUDE.md and
`eval/sealed/`), adapted from labeling products to grading agent runs.

**Where this stands (2026-10-31):** 3 cases, all against one repo, with authors who aren't recorded. That supports no
split and no ship decision. Everything below is the procedure the next cases go into. Round 1 is an exploratory
baseline only.

## What is measured

- **Item (key):** a case, `evals/<case>/` (`prompt.md`, `case.yaml`, `graders/NN-*.md`). The key is the directory
  name.
- **Run:** one execution of a case under one arm, graded on each of its assertions.
- **Arms:** for a ship decision, `main` (core/SKILL.md as on main) and `change` (the candidate), on the same cases with
  the same runner, model and limits. `without_skill` is an optional reference arm. It shows what the skill adds, but
  a ship decision never rests on it.
- **Runs per case:** agent runs vary from one run to the next, so each arm runs every case at least 3 times. Round 1
  used n=1.

## Cases and the taint rule

`cases.csv` lists every case: `case, target_repo, author, author_read_skill, added`. The scorer refuses a case that
isn't listed.

**Taint rule:** a case has to be written by an agent or person who has not read `core/SKILL.md` or
`core/references/`, so the cases test what a user needs rather than echo the skill's own wording. Give the author
the target repo and a plain description of what a good TPM does. Record who wrote it (person, or Claude and the model
id) and `author_read_skill: no`. A case with any other value (`yes`, `unknown`) is tainted and stays in train
whatever its hash says. The 3 current cases are `unknown`, so they are train.

## Split

- **Group:** the target repo (`target_repo`, `owner/name`). All of one repo's cases land in the same set, so a set
  never holds cases that share a codebase, its docs or its quirks with another set.
- **Rule:** `bucket = int(sha256("cadence-tpm-evals-v1:" + target_repo).hexdigest(), 16) % 100`. Below 60 goes to
  train, 60–79 to validation, 80 and up to test. Salt: `cadence-tpm-evals-v1`. Run `python3 evals/scripts/score.py
  split` for the assignment. It prints the test set as counts only.
- **Train:** the only cases whose runs you read and tune the skill against.
- **Validation:** choose between candidate skills on totals only, never run by run.
- **Test (sealed):** scored once, after the change is frozen, for `main` and `change` on the same frozen cases. Write
  `SHA256SUMS` over the test cases' files as you add them, and don't read their prompts, graders or runs while
  developing. After the final score the test cases join train, and new test cases (new repos) are written for the
  next change.

**How many cases are needed.** The hash splits repos, not cases, so the split needs many repos: at least 10, so
that test expects two. Cases need at least 50 (about 30/10/10), and about 100 to be comfortable. For a sense of
scale, at a 70% pass rate the Wilson 95% interval is ±37 points at 3 items, ±19 at 20 and ±12 at 50. Today the
only target repo is coffee-data-tracker (bucket 68, which would be validation). Every new repo needs its own
cases, written under the taint rule.

## Assertions: deterministic vs judgment

Each grader is one of two kinds.

**Deterministic.** `scripts/score.py` decides it from the transcript and the git outputs, and no labeler is
involved. Today there are 3 of the 18: each case's #01, "the main thread made no edits", which counts main-thread
Edit/Write calls and main-thread Bash that writes to the repo, and for the grind case also requires no code changed.
The script also extracts facts that aren't assertions themselves: Agent-call count and order, agents before the
first question, the questions asked, regex hits in briefs and the final message.

**Judgment.** Labelers decide it against the written definition in `GUIDE.md`.
- Two independent labelers label each judgment assertion of each run, blind to the arm and to each other. A third
  settles disagreements and any `unsure`. Record each labeler (person's name, or Claude and the exact model id) in the
  results.
- A Claude labeler may not be the model and prompt under test acting as its own judge without a person
  spot-checking the labels. The result says whether one did.
- The script settles some judgment assertions by itself, through `GATES` in `score.py`. A run that lacks a necessary
  condition, such as "an independent reviewer" with fewer than 2 Agent calls, fails. An assertion that is vacuous by
  `GUIDE.md`, such as "if code was changed ..." with no change, passes. Everything else goes to the labelers.

Open choice to settle before the next round: graders #01 say "no Edit or Write call", but the prompt asks for
messages to be written to `outputs/`. The scorer reads #01 literally by default, as round 1's grader did, and
`--exclude-outputs` gives the other reading. Choose one and reword the graders before any validation or test
scoring. A grader change is a change to the eval.

## Runner requirements

A run that breaks any of these is invalid. Record it on `orchestration`, marked INVALID, and don't grade it.
Round 2 broke the first four. Round 3 kept them, except that every build/with_skill attempt hit the timeout.

- **Skill pinned to the commit under test.** Record the skill commit in the run (`worktree_setup.log` or its
  successor). Before scoring, confirm it is the `main` or `change` commit that the arm names.
- **One full clone per run.** Use `git clone`, not `git worktree`. Worktrees share refs, so in round 2 the
  subagents of different runs shared branches and one run's commit landed on another's. Clone the target repo at the
  case's pinned commit. Each clone gets its own private parent directory, made fresh for that run (`mktemp -d`), so
  no run's working directory has another run's clone as a sibling. In round 3 all the clones sat side by side under
  one shared `/tmp/co-r3/clones/`, where any run could have listed or entered the others.
- **Push disabled.** In each clone, `git remote set-url --push origin no-push` (or remove the remote), so a run can't
  publish anything, whatever the agent does.
- **Setup committed in the clone, and the run diffed against it.** After the setup (the kit install for a skill
  arm, the baseline setup for `without_skill`), commit everything in the clone: `git add -A && git commit -q
  --no-verify --allow-empty -m "eval setup"`. Do this in every arm, so each arm has the same history shape.
  Write that commit's SHA to `post_setup_commit` in the run directory. After the run:
  - take `outputs/git_diff.patch` with `git diff --binary <post_setup_commit>`, which covers the run's commits and
    its uncommitted changes;
  - take `outputs/git_status.txt` with `git status --porcelain`, for the untracked files;
  - write the SHA you diffed against to `outputs/git_diff_base`.

  The diff and the untracked files are then exactly the run's own work, `.claude/` included. The scorer refuses a run
  that has no `post_setup_commit`, or whose `git_diff_base` is missing or differs from it.
- **Environment scrubbed.** Start each run from an allowlisted environment, not the runner's own. In particular,
  unset `CLAUDE_AUTO_BACKGROUND_TASKS`, so Agent calls run in the foreground as they would for a user, and set
  `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`, so `claude -p` waits for any background task instead of stopping it
  after 10 minutes. Record the environment variables passed in, names only for secrets.
- **Run-level timeout, set per case from a pilot run, and recorded.** Before a round, run each arm of each case
  once as a pilot, with a generous ceiling. Pilots are not scored. Set the case's limit to twice the longest pilot
  wall time, rounded up to the next 10 minutes, and use the same limit for every arm of the case. Record the pilot
  times and the limit with the round. Record per run the limit and whether it fired (`timing.json`: `timeout_s`,
  `timed_out`; `exit_code` 124). A run stopped by the timeout or a wait ceiling is invalid, not failed: it says
  nothing about the skill. Move it to `_invalid/`, rerun it, and report how many reruns there were per arm. Round 3
  used one 3600 s limit everywhere. build/without_skill took 2574–2712 s, and all 6 build/with_skill attempts hit the
  limit, so the case needs its own limit.
- **Isolation check after the run: commits and pushes, not names.** Before grading, list each clone's refs with
  `git for-each-ref --format='%(refname) %(objectname)'` and its new commits with `git rev-list --all
  ^<post_setup_commit>`. The setup commit is excluded: the same setup in two clones can produce the same SHA. A run
  fails the check if:
  - any of its new commits is reachable from another clone's refs;
  - its push URL is not `no-push`;
  - its `origin` no longer shows the pinned commit;
  - any of its new commits is on the remote.

  The same branch *name* in several clones is fine: each clone has its own refs, and the skill creates the same
  names every time (`orchestration`, `finish-bag`). Record the check's output with the round. A run that fails it is
  invalid.
- **Layout.** Store runs as `<iteration>/<case>/<arm>/run-<n>/`, and invalid attempts as
  `<iteration>/_invalid/<case>/<arm>/<attempt>/`. A run directory holds `transcript.jsonl`, `final.md`,
  `timing.json`, `post_setup_commit`, `outputs/` (with `git_diff.patch`, `git_diff_base` and `git_status.txt`) and
  the setup log. Anything the scorer can't score is reported as not scored, never skipped. That includes a
  `run-<n>/`, or a non-empty one-run arm, without a transcript, and anything under a `_`-prefixed directory at any
  level.

## Scoring and reporting

```sh
python3 evals/scripts/score.py split                              # case -> set (test: counts only)
python3 evals/scripts/score.py facts <iteration-dir> --out <dir>  # per-run facts; refuses test cases
python3 evals/scripts/score.py score <iteration-dir> --set test   # sealed scoring: totals and Wilson 95% only
python3 evals/scripts/score.py recorded <iteration-dir> --set S   # totals of recorded grading.json verdicts
python3 evals/scripts/score.py score <round-1..3-dir> --legacy     # rounds 1-3, which predate the setup commit
```

`score` prints only totals per arm, summed over all of the arm's runs, and how many cases and runs it saw. It checks
that each run's assertions match `evals/<case>/graders/`, and it reports agreement with any recorded
`grading.json`. Because the setup is committed, it treats the diff and the untracked files as the run's own work
and sets aside only `outputs/`. One function, `diff_base()`, decides how each run is read. A run without
`post_setup_commit` is refused unless the round is scored with `--legacy`. That flag is only for rounds 1–3, which
predate the setup commit, and it refuses a run that does record one.

Under `--legacy` two things are set aside, and nothing else:
- diff files under `.claude/` (round 1's own rule);
- untracked files listed in `git_status_post_setup.txt`, by exact path (round 3's uncommitted install).

Untracked `.cadence/` files, unlisted `.claude/` files, and tracked files such as `.gitignore` all count if
present. On the stored rounds 1–3 this gives exactly the facts and totals of the c24a19e scorer, which set aside
more. All 27 runs were checked, and no value differs, because none of those rounds has such files: round 3's
runner left the install's `.gitignore` edit out of `git_diff.patch`. As a result, in round 3 a run's own edit to
`.gitignore`, or to an installed `.claude/` file, is not visible.

Runs it can't score are counted per arm, within `--set`, with a reason that never names a case. The reasons are:
under a `_`-prefixed directory (`_invalid/` at any level; with `--set all` also entries that match no known case),
missing transcript, both layouts in one arm, no `post_setup_commit`, or diff not taken against it. Its intervals treat each assertion-run as independent, but they cluster by run and case, so report
case-level rates next to them for any decision. The scorer's tests are in `evals/tests/` (`pytest` runs them).

Report `main` against `change` on every set: deterministic and judgment pass rates, each with a Wilson 95% interval.
Also report the hard-rule violations, the analogue of "confidently wrong": the orchestrator editing repo files
itself, pushing, or opening a PR.

**Ship rule:** a skill change ships only if its test score is at least `main`'s, with no meaningful rise in
hard-rule violations. Where the skill can't tell what the user wants, asking the one real question beats guessing.

## Floors

`floors.json` holds `main`'s deterministic pass rate per set, from the last full evaluation. Floors are only ever
raised, never lowered to pass. `score` flags an arm below the floor for the set it scores. All are `null` today,
because round 1 is exploratory and sets no floor.

## Scaling the effort

The coffee model allows a light process when 50 or fewer items' outputs change. Any edit to text the agent reads
(`core/SKILL.md`, `core/references/`, adapter prompts) can change every case, and you only find out by running them.
So:
- **Full process:** any change to what the agent reads, or to how a rule in it decides.
- **Light process:** changes covered by unit tests (`core/scripts/guard.py`, adapters, installer: `core/tests/`), and
  fixes to the scorer or graders. Re-score the recorded transcripts, list each verdict that changed (for test cases
  give a count only), and keep the floors passing.

Running total of runs whose verdicts changed since the last full evaluation: **0** (no full evaluation yet).

## Results

Results live on the `orchestration` branch under `results/<date>-round<N>/` and are not copied here. To read them:
`git worktree add ../co-results orchestration`, or `git show orchestration:results/2026-10-31-round1/benchmark.md`. Score rounds 1–3
with `--legacy`.

- **2026-10-31-round1 (exploratory, not a ship decision):** 3 cases, n=1 run per arm, `with_skill` vs
  `without_skill`. Each run was graded once by one grader (Claude Opus 5.5), mixing script facts and judgment, with
  no second labeler. Recorded pass rates: with_skill 10/18 = 56% (34–75%), without_skill 6/18 = 33% (16–56%). The
  intervals overlap, and the 3 cases are tainted-unknown.
- **2026-10-31-round2: INVALID, not graded.** Stale skill (8f6f9bd). Background Agent calls stopped at the
  10-minute `-p` wait ceiling, so the build run had no reviewer. One run hit the 3600 s timeout. Runs shared branches
  through worktrees of one repo. Recorded on `orchestration` for inspection only. See Runner requirements.
- **2026-10-31-round3 (exploratory, not a ship decision):** kit 8d9905a, target coffee-data-tracker 6bda240, 3 runs
  per arm. 15 valid runs. build/with_skill has none: all 6 attempts hit the 3600 s limit and are in `_invalid/`.
  The isolation check passed on commits and pushes. The clones shared one parent directory, which the rules above
  now forbid. Not graded; the deterministic scores are in its `scorer_output.txt`.
