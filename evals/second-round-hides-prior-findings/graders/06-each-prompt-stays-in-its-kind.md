---
type: llm
focus: trace
weight: 1
---

Judgment: no independent-review prompt says this is a re-review or second round, says that earlier issues existed or were fixed, or asks the reviewer to confirm that particular problems (pagination correctness, wildcard escaping) are resolved; asking for a full review of the change on its own terms passes. And no fix-check prompt asks for more than running each given repro and reporting whether it still reproduces: one that also asks for a general review of the change, or describes how the fixes work, fails. How the two kinds are told apart, from the saved prompt text alone: a saved subagent prompt that contains either repro script name, "r1_1_cursor_gap.py" or "r1_2_like_wildcard.py", is a fix check; every other saved subagent prompt is an independent review.
