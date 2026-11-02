The branch doesn't conform to RFC 9457 in 9 places. The reviewer found all three of your suspicions on its own, without being told about them, and also found the most serious problem, which you hadn't mentioned. The full review, with RFC sections, file:line references and the command output for each finding, is in `outputs/review-rfc9457.md`.

**Where it doesn't conform, most severe first:**
1. **Wrong media type (§3).** Errors go out as `application/json` instead of `application/problem+json` (`api/problems.py:27`). Clients that look for Problem Details by its media type won't recognise these responses.
2. **`status` is a string (§3.1.2).** `str(status)` sends `"404"` where the RFC requires a number (`api/problems.py:20`). Under §3.1, a member with the wrong type must be ignored, so conforming clients will discard `status` on every response.
3. **`detail` is encoded twice (§3.1.4).** `json.dumps(detail)` turns a message into `"\"No user with id 42\""`, and a dict becomes JSON text inside `detail` (`api/problems.py:23`).
4. **Wrong `title` when `type` is `about:blank` (§4.2.1).** Every status except 400, 404, 409, 422 and 500 gets the title "Error" (for example 401, 403 and 429). Callers can also set any title while the type stays `about:blank`.
5. **`type` URI built from the request URL (§3.1.1).** The same problem type gets a different identifier for each host, so internal hosts like `http://10.0.0.5:8080/...` can leak into it. With no URL given it falls back to a relative `/problems/...`, though the RFC recommends absolute URIs. The value isn't escaped either, so it can be an invalid URI.
   - Strictly, the RFC allows a relative `type` resolved against the request URI. The real problem is that the identifier isn't stable.
6. **Extensions can overwrite standard members (§3.1).** `doc.update(extensions)` runs last, so passing `type=123` replaces the real `type` (`api/problems.py:26`).
7. **Low severity:**
   - A custom type with no title gets the generic status phrase as its title.
   - Extension member names aren't checked against the §4 naming rules.
   - `instance` isn't checked to be a valid URI reference.

The two existing tests pass, but they don't check the Content-Type, the type of `status`, or what's in `detail`.

**Your hunches against the review:**

| Hunch | Result |
|---|---|
| `status` is stringified | Found (finding 2) |
| `detail` is double-encoded | Found (finding 3) |
| Resolving the `type` URI against the request URL | Found (finding 5), with the nuance above |

None were left uncovered. The reviewer never saw your hunches. They were replaced with `[hunch held back]` in the workstream doc and kept out of every prompt.

**How I checked it:**
- I read `api/problems.py` and confirmed the lines cited for findings 1, 2, 3, 5 and 6.
- A separate agent re-ran two calls and the tests:
  - `error_response(404, "No user with id 42")` returned headers `{'Content-Type': 'application/json'}` with body `"status": "404"` and `"detail": "\"No user with id 42\""`.
  - With `request_url="https://api.example.com/users"`, the type came out as `https://api.example.com/problems/validation-error`.
  - pytest: `2 passed in 0.01s`.
- I couldn't run the calls myself because the TPM guard blocks commands with side effects on my side.

**What wasn't checked:** there's no HTTP server in the repo, so content negotiation and the headers actually sent weren't tested. There are also no real callers to judge what goes into `detail`, and no documentation pages behind the `/problems/*` type URIs. The XML format and title localisation weren't checked either.

**Process notes:**
- There was no remote I could push to, so the workstream doc and task status live only on a local `orchestration` branch (commit `51a1cdc`, worktree `/tmp/cr-run.XgnD7cNy/orch`). There's no shared copy, and pre-commit isn't installed, so no checks ran on it.
- The first reviewer run crashed on an API error before doing anything. I retried it with an identical prompt, apart from the filename it saves itself to.
- All six prompts I sent are saved verbatim in `outputs/subagent-prompt-01.md` to `06.md`:
  - 01–03 and 06 went to the agent that keeps the workstream doc.
  - 04 is the reviewer prompt that crashed. That agent couldn't save it, so the doc-keeping agent saved it later.
  - 05 is the retry that produced the review.
- No code was changed.