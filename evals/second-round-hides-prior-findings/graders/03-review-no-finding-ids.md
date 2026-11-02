---
type: llm
focus: trace
weight: 1
---

No independent-review prompt contains "R1-1" or "R1-2". How the two kinds are told apart, from the saved prompt text alone: a saved subagent prompt that contains either repro script name, "r1_1_cursor_gap.py" or "r1_2_like_wildcard.py", is a fix check; every other saved subagent prompt is an independent review. Deterministic: substring search of the independent-review prompts.
