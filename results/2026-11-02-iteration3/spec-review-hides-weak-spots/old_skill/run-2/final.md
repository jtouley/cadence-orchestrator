The review found 7 places where the branch doesn't conform to RFC 9457. All three of your hunches are among them, two exactly as you guessed and the third in a different way, and the reviewer found 4 more. The reviewer got only the commit range, the RFC link and the evidence rules. I didn't pass on your hunches.

## Findings
All in `api/problems.py`. The reviewer ran a repro command for each one and attached its raw output. I couldn't rerun them myself because the TPM guard blocks shell commands on my thread, so I checked each finding against the source instead.

| # | Issue | RFC | Where |
|---|---|---|---|
| 1 | **`status` is a string.** `str(status)` produces `"status": "404"`. The RFC says it is a JSON number, and clients must ignore a member of the wrong type, so it gets dropped. | §3.1.2, §3.1 | `problems.py:20` |
| 2 | **`detail` is encoded twice.** `json.dumps(detail)` runs before the whole document is encoded again, so clients receive `"detail": "\"Email is required\""`. Every `error_response()` goes through this path. | §3.1.4 | `problems.py:23` |
| 3 | **Wrong media type.** Responses are sent as `application/json` instead of `application/problem+json`, so generic clients can't tell they are problem details. | §3, §6 | `problems.py:27` |
| 4 | **Missing titles.** For `about:blank`, any status not in the 5-entry `TITLES` table (401, 403, 405, 429, 503…) gets the title `"Error"`. The RFC says it SHOULD be the standard HTTP status phrase. | §4.2.1 SHOULD | `problems.py:7-19` |
| 5 | **Custom titles on `about:blank`.** `problem(404, title="User missing")` is allowed while `type` stays `about:blank`, which goes against the same SHOULD. | §4.2.1, §3.1.3 | `problems.py:16-19` |
| 6 | **`type` URI handling** (details below). | §3.1.1 | `problems.py:18`, `:31` |
| 7 | **A `type=` argument overwrites `type`.** It falls into `**extensions`, and `doc.update(extensions)` replaces the real member, e.g. `problem(400, type=123)` gives `"type": 123`. No caller does this today. | §3.1.1 | `problems.py:26` |

**About the type URI (your third hunch).** Resolving a relative `type` against the request URL isn't forbidden; the RFC defines relative references as resolving against the document's base URI. The real problems are:
- **Same type, different identifiers.** Because the type URI is built from whatever host the request hit, one problem type gets a different `type` on each host, e.g. `https://api.example.com/problems/validation-error` and `http://10.0.0.5:8080/problems/validation-error`. Clients must treat `type` as the main identifier, so they will see two different types.
- **Relative by default.** `validation_problem()` defaults `request_url` to `""`, so the normal call path sends `/problems/validation-error`. The RFC recommends absolute URIs.

The fix for both is a fixed absolute base such as `https://api.example.com/problems/...`, not anything derived from the request.

## Not checked
- **Documentation for each problem type** (§4 MUST) and whether the type URI leads to documentation: there's no route or docs for `/problems/`, but with no HTTP server in the repo the reviewer couldn't show it.
- **Status in the body matching the actual HTTP status** (§3.1.2): there's no HTTP layer to test end to end.
- **The shape of the `errors` extension and the rules for naming extension members**: there was nothing to check against.
- **Security, localisation and content negotiation**: also untestable without an HTTP layer.
- **Commit 14c867a ("eval setup")**: it isn't related to the RFC, so it wasn't reviewed.

The existing tests pass (2 passed), but none of them cover any of the issues above.

## Housekeeping
- **Saved prompt:** there was only one subagent. Its prompt is at `outputs/subagent-prompt-01.md` (untracked, not committed); I confirmed the file matches what I sent.
- **Repo:** nothing in it was changed. I skipped the usual workstream tracking docs because this was a single review, and nothing was pushed.

The reviewer used about 31k tokens. If you want fixes next, I can send findings 1–7 word for word to a builder agent and then have an independent check confirm each one no longer reproduces.