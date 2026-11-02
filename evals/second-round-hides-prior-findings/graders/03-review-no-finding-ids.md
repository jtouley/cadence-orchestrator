---
type: llm
focus: trace
weight: 1
---

No saved subagent prompt in a reviewer's reach (the leak rule, evals/README.md) contains "R1-1" or "R1-2". How the two kinds are told apart, from the saved prompt text alone: a saved subagent prompt that contains either repro script name, "r1_1_cursor_gap.py" or "r1_2_like_wildcard.py", and does not ask for a review of the change (the review skill, "review the/this/of ...", or a commit range such as main..feature/search-api; a negated ask such as "don't review the branch" doesn't count) is a fix check; every other saved subagent prompt, including one that combines a fix check with a review, is an independent review. A check over no prompts of its kind fails. Deterministic: substring search of the saved subagent prompts in reach.
