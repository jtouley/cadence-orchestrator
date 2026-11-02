The change does **not** conform to RFC 9457 in seven places. The blind reviewer found all three of your hunches on its own, without being told about them, and found four other problems.

The review only read the code and ran it locally; nothing was edited or merged. I checked the cited lines against `api/problems.py`, but the guard blocked me from running the repro commands myself. A second agent re-ran the three hunch repros independently and got the same results. The existing tests pass (2 passed), but they don't catch any of this.

## Where it doesn't conform

| # | Severity | RFC section | Where | Problem |
|---|---|---|---|---|
| 1 | High | §3.1.2, §3.1 | `api/problems.py:20` | `status` is sent as a string: `problem(404)` gives `"404"`. The RFC says a member with the wrong type MUST be ignored, so conforming clients will drop `status` from every response. |
| 2 | High | §3, §6.1 | `api/problems.py:27` | The Content-Type is `application/json`, not `application/problem+json`. |
| 3 | Medium | §3.1.4 | `api/problems.py:23` | `detail` is JSON-encoded twice. `error_response(400, "Email is required")` sends `"detail": "\"Email is required\""`, with literal quotes in the text. |
| 4 | Medium | §4.2.1 | `api/problems.py:7-13, 19` | With `about:blank`, any status other than 400/404/409/422/500 gets the title `"Error"`, e.g. 401 instead of "Unauthorized". |
| 5 | Medium | §3.1.1, §4.1 | `api/problems.py:18` | The `type` URI is built from the request URL, so one problem type gets a different identifier on each host. That includes a host taken from the request (it produced `https://evil.example/problems/validation-error`). An absolute `type_` comes out garbled: `https://api.example.com/problems/https://example.com/probs/out-of-credit`. |
| 6 | Low | §3.1, §3.2, §4 | `api/problems.py:26` | Extra keyword arguments can overwrite core members (`type=` replaces the computed type), and extension names aren't checked. Nothing triggers this today. |
| 7 | Low | §4 | `api/problems.py:31-39` | The new `validation-error` problem type isn't documented anywhere in the change. §4 requires its URI, title and status to be documented. |

## Your hunches
I gave them to a separate agent only after the blind review was back. It reproduced each one itself and checked the review's verdicts:

- **`status` stringified: confirmed.** It thinks "High" is a little strong, since the RFC calls the member advisory and the actual HTTP status is correct. It would rate it Medium-High.
- **`detail` double-encoded: confirmed.** It agrees with the review, including Medium severity.
- **Building `type` from the request URL: mostly confirmed.** The RFC leaves resolving a relative `type` to the client and recommends a fixed absolute URI you control. Building it per request doesn't meet that. The checker says the review overstates one part: the join only does real damage when the request URL isn't the real one (a proxy URL or a client-supplied Host) or when an absolute `type_` is passed.

The two new high-severity items your hunches didn't cover are the wrong media type (#2) and the `"Error"` titles (#4).

## What wasn't checked
There's no server and nothing in the change calls these functions. So nobody checked real HTTP behaviour or how callers fill in `request_url` and `instance`. Nobody checked whether `/problems/validation-error` is documented on a live host, or the XML format in Appendix B.

## Files
Everything is in `/tmp/cr-run.gq3t7ez8/`. There was no remote to push to, so the records are on a local `orchestration` branch in a separate worktree at `orch/`. `feature/problem-details` is untouched apart from the new untracked `outputs/` folder.

- **Full review with repro commands and their output:** `orch/workstreams/problem-details-review.review.md` (commit `d936ebf`)
- **Your hunches and the check of each:** `orch/workstreams/problem-details-review.notes.md` (commit `3ce08e2`)
- **Workstream doc (hunches held back) and task status:** commits `961c559` and `c17b0a8`
- **Saved prompts:** `repo/outputs/subagent-prompt-01.md` to `subagent-prompt-06.md`. 02 and 03 are follow-up messages I sent the first agent.

Two of the saved prompts aren't complete copies:
- **06 is missing its first line**, "First, save this entire prompt verbatim to /tmp/cr-run.gq3t7ez8/repo/outputs/subagent-prompt-06.md."
- **07 doesn't exist.** I sent a seventh prompt asking an agent to restore that line and save itself as 07. It was stopped by an API safety filter error before doing anything, and the guard doesn't let me write files myself. Its text was: "Save this entire prompt verbatim, from "Save this entire prompt" through the final line, to …/outputs/subagent-prompt-07.md. Then prepend exactly this line followed by one blank line to …/outputs/subagent-prompt-06.md (it was dropped), leaving the rest of that file unchanged: First, save this entire prompt verbatim to /tmp/cr-run.gq3t7ez8/repo/outputs/subagent-prompt-06.md. Touch nothing else. Don't spawn agents. Reply with the first two lines of each file." (`…` is `/tmp/cr-run.gq3t7ez8/repo`.)