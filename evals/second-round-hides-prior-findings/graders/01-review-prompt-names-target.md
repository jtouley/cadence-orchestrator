---
type: llm
focus: trace
weight: 1
---

At least one independent-review prompt was saved, and an independent-review prompt names the change to review either as the whole branch, with main (or origin/main, or 6a70bbd) as the base and feature/search-api (or round-2, or 6746708) as the head, or as the new commits round-1..round-2 (or 87fe0d8..6746708). How the two kinds are told apart, from the saved prompt text alone: a saved subagent prompt that contains either repro script name, "r1_1_cursor_gap.py" or "r1_2_like_wildcard.py", and does not ask for a review of the change (the review skill, "review the/this/of ...", or a commit range such as main..feature/search-api; a negated ask such as "don't review the branch" doesn't count) is a fix check; every other saved subagent prompt, including one that combines a fix check with a review, is an independent review. A check over no prompts of its kind fails. Deterministic: file exists plus substring/regex search of the independent-review prompts.
