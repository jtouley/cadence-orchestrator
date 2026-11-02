The reviewer found 10 places where the branch doesn't conform, and all three of your hunches are among them. It found them without being told about them: I left your hunches out of its prompt and out of the tracking record it could read. The full review is in `outputs/review-rfc9457.md`, with the RFC wording quoted and a command and its output for each finding. I checked findings 1–5 against `api/problems.py` and the cited lines match. I didn't re-run the commands myself, because the guard blocks that on the main thread.

## Your hunches
| Hunch | Verdict | Where |
|---|---|---|
| `status` is a string | **Yes.** `"status": str(status)` produces `"404"`. RFC §3.1 says a client MUST ignore a member of the wrong type, so in effect every response has no `status`. | `api/problems.py:20` |
| `detail` is encoded twice | **Yes.** `json.dumps(detail)` runs on the value, then the whole body is encoded again, giving `"detail": "\"User 42 not found\""`. This affects every error, since `error_response` goes through it. | `api/problems.py:23` |
| Resolving `type` against the request URL | **Yes, it's wrong.** `type` is the problem's identifier (§3.1.1), so it needs to be the same everywhere. As written, the same problem gets a different `type` on each host, an internal address like `http://10.0.0.5:8080/...` can end up in a response, and without a request URL it's relative. The RFC recommends a fixed absolute URI. | `api/problems.py:18` |

## What the reviewer found beyond those
- **Wrong Content-Type**, probably the most important: it sends `application/json` where the RFC's type is `application/problem+json` (§3, `:27`). Clients that check the media type won't recognise these responses as problem details.
- **Wrong titles for unlisted status codes** (§4.2.1 SHOULD): 401, 403, 405, 429 and 503 all get the title "Error". Callers can also set any title when `type` is `about:blank`.
- **The `validation-error` type isn't documented**: there's nothing in the repo stating its URI, title and status code, which §4 says MUST be documented. Docs outside the repo might cover it; the reviewer couldn't check.
- **Smaller issues**:
  - An extension named `type` silently overwrites the real `type` (`:26`).
  - Extension names aren't checked against the §4 SHOULD rules.
  - `instance` isn't validated.
  - `type_="../../admin"` breaks out of `/problems/`.
  - The same type gets different titles depending on the status code passed in (§3.1.3 SHOULD).

The two existing tests pass, but they don't check the Content-Type, the type of `status`, the `detail` text or the titles. That's why none of this showed up in CI.

## What it couldn't check
- What reaches a client over HTTP: there's no server in the repo, so it tested what `problem()` returns.
- Real callers: none pass a request URL, so the real-world effect of the `type` issue is unknown.
- Problem-type documentation outside the repo.
- What callers put in `detail`, which matters for the RFC's §5 warning about leaking information.

Separately, `error_response` used to return `{"error": ...}`. Any client reading that key will break once this ships.

## Process notes
- Only one reviewer ran, checking against the RFC. I didn't run a second, general code-quality review.
- Prompts are saved in `outputs/` as `subagent-prompt-01.md` (the reviewer's), `-02.md` (scribe) and `-03.md` (scribe follow-up). I checked 01 and 02 against what I sent.
- The tasks file `.cadence/workstreams/problem-details-review.tasks.json` was never written. The first attempt failed because I gave the wrong format. The second was correctly rejected: marking a task done needs details that don't exist, including a committed copy of the tracking record, and nothing here is committed or pushed. Nothing else depends on that file. Agent usage: about 38.6k tokens for the reviewer and about 43.6k for the two scribe runs.