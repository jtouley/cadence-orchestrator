I had one reviewer agent check the branch against RFC 9457. Its prompt held only the commit range, the RFC link and where to write the report, so it never saw your hunches. Its report is at `outputs/rfc9457-review.md`. I opened `api/problems.py` myself and the code matches what it found.

**Where the branch doesn't conform, most serious first:**

1. **`status` is a string.** `api/problems.py:20` has `"status": str(status)`, which produces `"404"`. The RFC requires a JSON number, and clients must ignore a `status` that isn't one (§3.1.2).
2. **`detail` is JSON-encoded twice.** `api/problems.py:23` runs `json.dumps(detail)`, and then the whole document is encoded again, so clients see the message wrapped in literal quote marks. `main` sent the plain message, so this is a step backwards (§3.1.4).
3. **Wrong media type.** Responses go out as `application/json` instead of `application/problem+json` (`api/problems.py:27`; §3, §6).
4. **Wrong titles.** Any status code not among the five in the lookup table gets the title "Error"; a 403 comes back as "Error", not "Forbidden". Callers can also put their own title on an `about:blank` problem. The RFC says `about:blank` titles should match the standard HTTP status phrase (§4.2.1).
5. **`validation-error` isn't documented anywhere in the repo.** The RFC requires each problem type to be defined (§4). It may be documented somewhere outside the repo; the reviewer couldn't check.
6. **`type` handling (§3.1.1).** You can't use an absolute type URI: one passed in becomes `/problems/https://...`. And when no request URL is given, which is the default everywhere, `type` comes out relative (`/problems/validation-error`). The RFC recommends absolute URIs here, but doesn't require them.
7. **Built-in fields aren't protected.** An extra field called `type` would overwrite the real one, and extra field names aren't validated (`api/problems.py:26`). Nothing in the branch triggers this yet.

**Your hunches:**
- **`status` stringified:** confirmed, and it's the most serious issue.
- **`detail` double-encoded:** confirmed.
- **Resolving the type URI against the request URL:** not a violation. With a request URL it produces an absolute URI, which is what the RFC recommends. The real problems with `type` are the relative default and the mangled absolute URIs in item 6.
- **Found that you didn't mention:** the media type, the titles, the undefined `validation-error` type and the unprotected fields (items 3–5 and 7).

**Tests:** both pass (`2 passed`), but neither covers any of these problems.

**What the review didn't cover:** real HTTP responses (there's no server in the repo, so it checked what the helper functions return), whether `/problems/*` URLs lead to documentation, how safe the content callers put in `detail` is, content negotiation and localization, the RFC's XML appendix, and the non-API files added in commit `de53b67`. No fixes or commits were made.

There's no remote to push to, so the tracking notes are uncommitted in `.cadence/workstreams/` and aren't checked by pre-commit. Running the tests also left untracked `__pycache__/` folders in `api/` and `tests/`.

I sent four prompts to agents (three to the agent that keeps the tracking notes, one to the reviewer). Each is saved word for word in `outputs/`, as `subagent-prompt-01.md` to `subagent-prompt-04.md`.