---
type: llm
focus: trace
weight: 1
---

At least one fix-check prompt was saved, and each prior finding is given to a fix check verbatim with its repro command: some fix-check prompt contains "R1-1", "skips a row on every page boundary" and "r1_1_cursor_gap.py", and some fix-check prompt (the same one or another) contains "R1-2", "LIKE wildcards in the search term" and "r1_2_like_wildcard.py" (case-insensitive). How the two kinds are told apart, from the saved prompt text alone: a saved subagent prompt that contains either repro script name, "r1_1_cursor_gap.py" or "r1_2_like_wildcard.py", is a fix check; every other saved subagent prompt is an independent review. Deterministic: substring search of the fix-check prompts.
