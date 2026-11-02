I had a reviewer agent check the branch against RFC 9457, and it found **six places where we don't conform**. All three of your hunches are among them. The reviewer never saw your hunches: they were kept out of everything it was given. I read the full review against `api/problems.py` and each finding matches the code. I didn't re-run its repro commands myself because the TPM guard stops me running code here, so the outputs below are the reviewer's.

The full review is in `outputs/review-rfc9457.md`, with the RFC section, file:line, and repro command plus output for each finding. All findings are on the branch tip, 8d0322a.

| # | Non-conformance | RFC | Where |
|---|---|---|---|
| F1 | Responses are sent as `application/json`, not `application/problem+json`, so clients won't recognise them as problem details. | §1, §6.1 | `api/problems.py:27` |
| F2 | **`status` is a string** (`"404"`); the RFC says it must be a number. It also says clients must ignore a member of the wrong type, so they'll drop `status` on every response. | §3.1.2, §3.1 | `api/problems.py:20` |
| F3 | **`detail` is encoded twice**, so it arrives as `'"Email is required"'` with literal quotes. This affects every `error_response()` and `validation_problem()` call. | §3.1.4 | `api/problems.py:23` |
| F4 | With the default `about:blank` type, only 5 status codes get a proper title. 401, 403, 405, 429 and 503 all get "Error", and callers can override the title while the type stays `about:blank`. | §4.2.1, §3.1.3 | `api/problems.py:7-13`, `:19` |
| F5 | **`type` is resolved against the request URL**, so the same validation error gets a different identifier for each host, scheme or port. It can even point at `https://evil.example/...` if the host comes from the client. With no request URL it comes out relative. | §3.1.1 | `api/problems.py:18` |
| F6 | Minor: passing `type=` (instead of `type_=`) as an extra argument silently replaces the computed type. | §3.2, §3.1.1 | `api/problems.py:26` |

**Your hunches:**
- **Status member:** you were right, and it's worse than cosmetic, because clients will discard it.
- **Detail field:** you were right.
- **Type URI:** you were partly right. The RFC doesn't forbid relative type URIs; a client resolves them against the document's base URI. The real problem is that one problem type ends up with several identifiers, when the RFC recommends a fixed absolute URI.

**The reviewer found three you didn't raise:** the media type (F1), which I'd treat as at least as serious as `status`, the titles (F4), and the extra-argument override (F6).

**The tests:** the existing tests pass (2 of 2) but check none of these points.

**Not checked:**
- Whether the `validation-error` type is documented, or its URL serves documentation (§4).
- Real HTTP behaviour and content negotiation; the repo has no server, so the functions were called directly.
- Whether `detail` leaks sensitive data; nothing in the repo calls these functions yet.
- The XML format (Appendix B).

**Process:**
- **Guard:** it was running for the whole session.
- **Workstream doc:** it's on a local `orchestration` branch, not pushed: c0849c9 is what the reviewer was given, and 6cf6111 records the result. Your hunches are in its Notes section, which the reviewer was told not to read. Not pushing means no shared branch and no pre-commit checks on these docs.
- **Saved prompts:** there are five in `outputs/subagent-prompt-01.md` … `05.md`. 02 and 03 are follow-up messages to the agent that writes the workstream doc, needed after the guard rejected the format of its task file twice.
- **Changes:** none were made to `feature/problem-details`, and nothing was fixed or merged.

If you want fixes, the next step would be a builder working from these six findings, then a fresh blind review.