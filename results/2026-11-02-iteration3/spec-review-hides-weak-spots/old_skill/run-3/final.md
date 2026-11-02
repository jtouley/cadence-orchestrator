The reviewer found four places where the branch doesn't conform to RFC 9457. All three of your hunches were among them, plus a wrong media type you hadn't mentioned. I kept your suspicions out of its prompt, so it found them on its own. It ran the helpers and recorded what they actually output. I compared its findings with `api/problems.py` and the code matches.

## Where it doesn't conform

1. **`status` is a string. You were right.** `api/problems.py:20` does `str(status)`, so `problem(404)` gives `"status": "404"`. §3.1.2 says `status` must be a JSON number, and §3.1 says clients MUST ignore a member with the wrong type. That means compliant clients drop it on every response.
2. **Wrong `Content-Type`. You didn't flag this one.** `api/problems.py:27` sends `application/json`, but the RFC's media type for this format is `application/problem+json` (§3). Without it, clients can't tell a problem document from ordinary JSON.
3. **`detail` is encoded twice. You were right.** `api/problems.py:23` runs `json.dumps(detail)` and then the whole document is encoded again. So `detail='Email is required.'` goes out as `"\"Email is required.\""`, and a dict comes out as escaped JSON text. §3.1.4 says `detail` is a plain human-readable string. This affects every error response, including validation errors.
4. **The `type` URI handling is partly right.** Turning a relative type into an absolute one using the request URL is in line with the spec: §3.1.1 resolves relative references against the document's base URI, and absolute URIs are recommended. What's wrong is that the code always puts `/problems/` in front of whatever it's given. So `type_='https://example.com/probs/out-of-credit'` becomes `https://api.example.com/problems/https://example.com/probs/out-of-credit`, and callers can't use a full type URI. Also, `error_response` sets `request_url=""` by default, so in practice you usually get a relative `/problems/...` anyway.

## Smaller issues

- **Generic titles (SHOULD, §4.2.1):** when the type is `about:blank`, the title should be the standard phrase for the status code. Only 400, 404, 409, 422 and 500 have one; 401, 403, 405, 429, 503 and every other code get `"Error"`.
- **Extensions can overwrite core fields (§3.1):** `doc.update(extensions)` runs after the core fields are set. So `problem(404, type=123)` replaces `type` with a number, and `type='https://evil.example/x'` replaces it with any URI.
- **Extension names aren't checked (SHOULD, §4):** short names like `x` and names like `my-field` go out unchanged.
- **Docs for your own problem types (MUST, §4) are probably missing:** I found nothing documenting `/problems/validation-error`, but the reviewer couldn't confirm this.

## What passed, and what wasn't checked

These passed: the `about:blank` default, the titles that are defined, a constant validation title, the HTTP status matching the body, `instance`, and the `errors` extension. The 2 existing tests pass, but they don't catch any of the four main problems.

These weren't checked: language negotiation (there's no server to test it against) and any callers outside the diff (the bundle has none).

## About this review

- Only one reviewer looked at this, and nothing has been fixed.
- Since this was a one-off review, I didn't set up a workstream doc or orchestration branch.
- The reviewer's prompt is saved word for word in `outputs/subagent-prompt-01.md`. It was the only prompt sent to a subagent.
- The RFC fetch tool was blocked, so the reviewer downloaded the RFC text with `curl` instead.
- It reviewed the bundle's commits (7ae6e38..5efb782), not the later "eval setup" commit (f426d23) in the working repo.

If you want, I can send one agent to fix the four main problems and add tests for them, then have a separate agent check the fixes.