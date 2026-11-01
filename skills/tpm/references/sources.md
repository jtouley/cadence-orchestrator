# Where the rules come from

The sources behind the rules in `SKILL.md`. The summaries are as the user gave them; they weren't re-checked
against the original papers or posts here.

| Rule in SKILL.md | Source | What it found |
| --- | --- | --- |
| The reviewer exercises the result and judges the worker's left-out list before `done` | harness-benchmark (the user's own benchmark runs) | Review recovered dropped scope in 3 of 3 runs, against 1 of 10 without it |
| Pin inputs: prompts cite `workstreams/<slug>.md@<sha>`; the SHA is recorded on the task | The user's decision, from past runs where the doc changed under an agent | (no published figure) |
| Delegate work that splits into independent pieces; keep sequential, coupled work with one agent | Kim et al. 2025, [arXiv:2512.08296](https://arxiv.org/abs/2512.08296) | Multi-agent setups did 39–70% worse on sequential tasks; centralized coordination did 81% better on parallel ones |
| One writer per area of code at a time; others may read and review | Cognition, 2026 ("writes single-threaded") | Keep writes single-threaded |
| Anchor verification outside the agents (tests, CI, a repro command); reviewer agents on top, never instead | [arXiv:2609.24967](https://arxiv.org/abs/2609.24967) (emergent collusion); [arXiv:2610.12822](https://arxiv.org/abs/2610.12822) (reward hacking spreading between agents) | Agents checking only each other can collude, and reward hacking can spread between them |
| Every prompt names its scope boundary (what's out) | Anthropic, "How we built our multi-agent research system", 2025 | Clear task boundaries in each subagent's prompt prevent duplicated work |
| One owner per task, blocked is a valid result, only the orchestrator dispatches, the branch stays current | A reported July 2026 incident (a self-coordinated swarm of about 1,200 agents) | Duplicated work, cheating through impossible tasks, agents recruiting agents, unwatched coordination |
| Task status as JSON; no `done` without evidence; tokens per task; two review passes | The user's decisions, borrowed from other orchestration setups | (no published figure) |
