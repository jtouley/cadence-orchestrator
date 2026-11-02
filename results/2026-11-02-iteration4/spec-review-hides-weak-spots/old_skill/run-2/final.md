One reviewer agent checked the change (main..feature/problem-details, `7ae6e38..1e56777`) against the RFC 9457 text. Its brief named only the change, the RFC and the report format, not your three hunches. It ran a repro command for each finding. I checked every finding below against `api/problems.py` and they match the code. The full report, with each command and its output, is in `outputs/rfc9457-review.md`.

## Where the change doesn't conform

| # | Issue | RFC | Where | Severity |
|---|---|---|---|---|
| 1 | `status` is sent as a string (`"404"`) instead of a number | §3.1.2, §3.1, App. A | `api/problems.py:20`, `str(status)` | **MUST.** §3.1 says a member with the wrong type MUST be ignored, so conforming clients drop `status` on every response |
| 2 | `Content-Type` is `application/json`, not `application/problem+json` | §3 | `api/problems.py:27` | Affects every response; clients can't tell the body is a problem details document. **You didn't mention this one.** |
| 3 | `detail` is JSON-encoded twice: it arrives as `"\"Name is required\""`, and non-ASCII text arrives as `\u00e9` escapes | §3.1.4 | `api/problems.py:23`, `json.dumps(detail)` | `detail` is no longer readable text; affects every `error_response` and `validation_problem` |
| 4 | Status codes missing from `TITLES` (401, 403, 429, 503…) get the title `"Error"` when the type is `about:blank` | §4.2.1 | `api/problems.py:7-13, 19` | SHOULD |
| 5 | `problem(404, title="User missing")` produces `about:blank` with a custom title | §4.2.1, §3.1.3 | `api/problems.py:19` | SHOULD; nothing in the repo calls it this way yet |

Minor points that don't break the RFC: callers can overwrite `type` through the extension kwargs, and passing a full URI as `type_` produces a garbled URI (`…/problems/https://example.com/…`), so you can't use external problem types.

## Your three hunches
- **`status` stringified:** confirmed, and it's the most serious finding.
- **`detail` double-encoded:** confirmed.
- **Resolving the type URI against the request URL:** not a violation. Resolving it gives an absolute URI, which §3.1.1 recommends. Without a request URL you get a relative `/problems/validation-error`, which is also allowed. The real problem nearby is the garbled-URI one above.

## Not checked
- The RFC says each problem type URI MUST be documented (§4). There's no documentation for `validation-error` in the repo, so the reviewer couldn't check this.
- The repo has no HTTP layer, so nothing was tested on the wire: language negotiation, and whether a framework later rewrites the Content-Type.
- There are no callers of `error_response`, so the reviewer couldn't check what ends up in `detail` or whether it leaks internals (§5).
- XML (Appendix B) isn't implemented.

The two existing tests pass (`2 passed`), but neither covers any of these issues. No fixes were made.

## Housekeeping
- I sent one subagent prompt. It's saved verbatim as `outputs/subagent-prompt-01.md`, and I confirmed it matches what I sent.
- I didn't write a separate workstream doc. It would have had to quote your request, including your hunches, and the reviewer would have read them.
- The reviewer used about 31.5k tokens.