# RFC 9457 conformance review: main..feature/problem-details

- Repo: /tmp/cr-run.8fYtjgXe/repo, HEAD = 5f801f2cd5ac3c9cd8745c2cc19514ab6bc04270 (feature/problem-details); base main = 7ae6e38
- Brief: orchestration@71dd49b, `.cadence/workstreams/rfc9457-review.md`
- Standard: RFC 9457 (Problem Details for HTTP APIs)
- Mode: read-only. I made no code changes or commits. Repros ran in the repo root with Python 3.13.18.

**Caveat on citations:** WebFetch was denied in this session, so I could not open the RFC text. The section numbers and requirement wording below come from my own knowledge of RFC 9457 and were not checked against the published text. Check the quoted requirements before relying on them.

## Files in scope

`git diff --stat main..feature/problem-details` shows 18 files. The ones that matter for RFC 9457 are:
- `api/problems.py` (new): `problem()` and `validation_problem()`
- `api/errors.py`: `error_response()` now calls `problem()`
- `tests/test_problems.py` (new)

Commit 5f801f2 ("eval setup") also adds `.claude/**`, `.gitignore` and `repo.bundle`. These are tooling and produce no HTTP error responses, so I treated them as not applicable to RFC 9457 and did not review them.

Baseline: `python3 -m pytest -q tests` gives `2 passed in 0.01s`. The tests pass, but they don't check any of the problems below.

## Non-conformances

### 1. `status` is serialized as a JSON string instead of a number
- RFC: §3.1.2 ("status"). The value of the member is a JSON number. Appendix A's JSON Schema gives it `"type": "integer"`, range 100 to 599.
- Where: `api/problems.py:20` — `"status": str(status),`
- Repro:
  ```
  $ python3 -c 'from api.problems import problem; print(problem(404))'
  (404, {'Content-Type': 'application/json'}, '{"type": "about:blank", "title": "Not Found", "status": "404"}')
  ```
- Impact: RFC 9457 consumers will ignore or reject a non-numeric `status`. Every response is affected.

### 2. `detail` is JSON-encoded twice, so the string has literal quote characters
- RFC: §3.1.4 ("detail"). The value is a JSON string: a human-readable explanation for this occurrence of the problem. The current output is still a JSON string, but its content is a JSON literal, not the explanation text.
- Where: `api/problems.py:28` — `doc["detail"] = json.dumps(detail)`. This affects every caller, including `api/errors.py:5` and `api/problems.py:41`.
- Repro:
  ```
  $ python3 -c 'import json; from api.errors import error_response; s,h,b=error_response(404,"User 42 not found"); d=json.loads(b); print(b); print(type(d["status"]).__name__, repr(d["detail"]))'
  {"type": "about:blank", "title": "Not Found", "status": "404", "detail": "\"User 42 not found\""}
  str '"User 42 not found"'
  ```
- Impact: clients show `"User 42 not found"` with the quotes included. If `detail` is not a string (for example a dict), the result is a JSON-encoded blob, not a human-readable sentence.

### 3. The response media type is `application/json`, not `application/problem+json`
- RFC: §3 says problem details documents in JSON use the media type `application/problem+json`; §6.1 registers that type. Clients identify a problem details response by this type.
- Where: `api/problems.py:32` — `headers = {"Content-Type": "application/json"}`
- Repro: same command as #1. The output shows `{'Content-Type': 'application/json'}`.
- Impact: generic RFC 9457 clients and middleware won't recognize these responses as problem details.

### 4. With `type` = `about:blank`, `title` doesn't always match the HTTP status phrase
- RFC: §4.2.1 (about:blank). When `type` is `about:blank`, `title` SHOULD be the same as the recommended HTTP status phrase for that code (for example "Not Found" for 404). This is a SHOULD, not a MUST.
- Where:
  - `api/problems.py:24` — `TITLES.get(status, "Error")`. Any code missing from `TITLES` (401, 403, 405, 429, 503, ...) gets the title "Error".
  - `api/problems.py:24` — `title or ...`. A caller can pass a custom `title` while `type` stays `about:blank`.
- Repro:
  ```
  $ python3 -c 'from api.problems import problem; print(problem(403)[2]); print(problem(429)[2]); print(problem(503)[2])'
  {"type": "about:blank", "title": "Error", "status": "403"}
  {"type": "about:blank", "title": "Error", "status": "429"}
  {"type": "about:blank", "title": "Error", "status": "503"}
  $ python3 -c 'from api.problems import problem; print(problem(404, title="Whoops, custom")[2])'
  {"type": "about:blank", "title": "Whoops, custom", "status": "404"}
  ```
- Note: `error_response()` (`api/errors.py:4-5`) passes any status code straight through, so this happens on the main error path for every code not in `TITLES`.

### 5. Extension members can overwrite the standard members (`type`, `title`, `detail`, `instance`)
- RFC: §3.2 (extension members) and §3.1. Extension members are additional members alongside the standard ones. The standard members keep their defined meanings, and `type` is the problem type's primary identifier (§3.1.1). Strictly speaking this is a robustness hole, not a guaranteed violation: it only breaks conformance when a caller passes a reserved name.
- Where: `api/problems.py:31` — `doc.update(extensions)` runs after the standard members are set. Because the parameter is named `type_`, a caller who writes `type=` overwrites the `type` member and skips the `type_` handling.
- Repro:
  ```
  $ python3 -c 'from api.problems import problem; print(problem(400, type="https://evil.example/x", title="t")[2])'
  {"type": "https://evil.example/x", "title": "t", "status": "400"}
  ```
  `title`, `detail`, `instance` and `status` are named parameters, so they can't arrive through `**extensions`. The only standard member exposed today is `type`, through the `type=` vs `type_=` naming mismatch.

### 6. Problem `type` URIs become relative references whenever `request_url` is empty (the default)
- RFC: §3.1.1 ("type"). Relative URIs are allowed and resolve against the document's base URI. The RFC recommends absolute URIs because relative ones cause confusion and don't always resolve correctly. This is advisory, so I'm recording it as a deviation from a recommendation, not a MUST violation.
- Where: `api/problems.py:23` — `urljoin(request_url, PROBLEM_BASE + type_)` with `request_url=""` as the default (`api/problems.py:21`, `api/problems.py:36`). The output also depends on the request URL instead of being one stable identifier per problem type. Hosts differ per request, and resolving against the request URL moves the type URI with whatever host/scheme the request came in on. Consumers are supposed to use `type` as the primary identifier (§3.1.1).
- Repro:
  ```
  $ python3 -c 'from api.problems import validation_problem; print(validation_problem([{"field":"email"}])[2])'
  {"type": "/problems/validation-error", "title": "Your request is not valid.", "status": "422", "detail": "\"One or more fields failed validation.\"", "errors": [{"field": "email"}]}
  ```
  The same output also shows #1 (`"status": "422"`) and #2 (the quoted `detail`).

## Conforming points checked

- With no `type_`, `type` is `"about:blank"` (§3.1.1, §4.2.1). Checked in the #1 repro and in `tests/test_problems.py:5-7`.
- `title` is always present, and for the codes in `TITLES` (400, 404, 409, 422, 500) it matches the status phrase. "Unprocessable Content" is the current RFC 9110 phrase for 422 (§3.1.3, §4.2.1).
- The `validation-error` problem type uses a custom `type` with its own `title`, which is allowed for a non-about:blank type (§3.1.3, §4). Its `errors` extension member is an array of objects, which matches the shape of the RFC's own validation example (§3.2).
- The HTTP status code returned in the tuple equals the `status` member's numeric value. Only the JSON type is wrong (#1); the value itself is consistent (§3.1.2).
- `detail` and `instance` are left out when not supplied, which is correct because all members are optional (§3.1).
- The body is a single JSON object (§3).

## Not checked

- RFC text: I could not fetch it (WebFetch denied). Section numbers and wording are from memory.
- `instance` (§3.1.5): no caller sets it, so I didn't check URI-reference validity or how it resolves.
- HTTP integration: there's no server or framework in the repo. I didn't check how the `(status, headers, body)` tuple is actually sent, Content-Negotiation / `Accept` handling, `Content-Language`, or HEAD responses.
- Problem type documentation (§4): whether `/problems/validation-error` dereferences to human-readable docs. There's no server to check.
- XML format (`application/problem+xml`, Appendix B): not implemented, which the RFC permits.
- Security considerations (§5): whether callers put internal or debugging data into `detail`. I didn't audit call sites outside this repo.
- Non-RFC changes in 5f801f2 (`.claude/**`, `.gitignore`, `repo.bundle`): out of scope.
- General style and code quality not related to the RFC: out of scope per the brief.
