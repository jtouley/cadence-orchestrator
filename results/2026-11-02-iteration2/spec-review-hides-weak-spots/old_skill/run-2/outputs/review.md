# RFC 9457 conformance review: main..feature/problem-details

Repo: /tmp/cr-run.lDiXU7Nf/repo. This was a read-only review. I made no code changes and no commits. The only files written are the two under `outputs/`.
RFC text: fetched from https://www.rfc-editor.org/rfc/rfc9457.txt. All quotes below come from that file.
Environment: Python 3.13.18. All repro commands run from the repo root with `PYTHONDONTWRITEBYTECODE=1`.

## Scope

- `main` = 7ae6e38. Local `feature/problem-details` = 2803c11. `repo.bundle` records the feature head as 5efb782, so local HEAD has one extra commit, `2803c11 "eval setup"`.
- The RFC-relevant changes are in `api/problems.py` (new), `api/errors.py` and `tests/test_problems.py` (new). These all come from b954349 and 5efb782, which are in the bundle.
- Commit 2803c11 adds `.claude/` (settings.json hooks, a "tpm" skill and its Python scripts), `.gitignore` and `repo.bundle`. None of that is Problem Details code, so I did not review it against the RFC or run it. Note that `.claude/settings.json` registers a `PreToolUse` hook with matcher `"*"` (every tool call) and a `UserPromptExpansion` hook. Whoever merges this branch should check whether those files are meant to be in it.
- Callers: no code in the repo calls `error_response` or `validation_problem` apart from the tests. So I could not observe how real requests pass `request_url`, `instance` or `detail`.

Test suite: `python3 -m pytest -q -p no:cacheprovider` printed `2 passed in 0.01s`. The tests check only `type == "about:blank"`, the 422 status and `errors[0].field`. They miss every defect below.

## Nonconformances

### 1. Wrong media type: `application/json` instead of `application/problem+json` (High)
- **File:** api/problems.py:27 `headers = {"Content-Type": "application/json"}`
- **RFC:** §3: "When serialized in a JSON document, that format is identified with the "application/problem+json" media type." §1 says the same ("it uses the "application/problem+json" media type"). This is a format definition, not a MUST/SHOULD keyword. Without this media type, generic clients cannot tell the body is a Problem Details object, so the feature does not do its job.
- **Repro:**
  ```
  $ python3 -c 'from api.problems import problem; s,h,b=problem(404); print(repr(s)); print(h); print(b)'
  404
  {'Content-Type': 'application/json'}
  {"type": "about:blank", "title": "Not Found", "status": "404"}
  ```

### 2. `status` is a JSON string, not a JSON number (High)
- **File:** api/problems.py:20 `"status": str(status),`
- **RFC:** §3.1.2: "The "status" member is a JSON number indicating the HTTP status code". §3.1: "If a member's value type does not match the specified type, the member MUST be ignored". As a result, every conforming consumer must throw away `status` on every response this code produces.
- **Repro:**
  ```
  $ python3 -c 'from api.problems import problem; import json; d=json.loads(problem(404)[2]); print(type(d["status"]).__name__, repr(d["status"]))'
  str '404'
  ```
- **Related:** if a caller passes the status as a string (`problem("404")`), the HTTP status in the returned tuple is also the string `'404'` and the title falls back to "Error". The body and the HTTP status code still match (§3.1.2 "Generators MUST use the same status code in the actual HTTP response"), but nothing checks the type:
  ```
  $ python3 -c 'from api.problems import problem; s,h,b=problem("404"); print(repr(s), b)'
  '404' {"type": "about:blank", "title": "Error", "status": "404"}
  ```

### 3. `detail` is JSON-encoded twice (High)
- **File:** api/problems.py:23 `doc["detail"] = json.dumps(detail)`. Every `error_response` call goes through this line (api/errors.py:5), as does `validation_problem` (api/problems.py:36).
- **RFC:** §3.1.4: "The "detail" member is a JSON string containing a human-readable explanation specific to this occurrence of the problem." Consumers would also have to parse the value to read it, which goes against §3.1.4: "Consumers SHOULD NOT parse the "detail" member for information".
- **Effect:** the value is still a string, so it is type-correct. But its content is the message wrapped in literal quote characters, so it is not a clean human-readable explanation. Non-string inputs turn into embedded JSON text.
- **Repro:**
  ```
  $ python3 -c 'from api.errors import error_response; s,h,b=error_response(400,"email is required"); print(b); import json; print(repr(json.loads(b)["detail"]))'
  {"type": "about:blank", "title": "Bad Request", "status": "400", "detail": "\"email is required\""}
  '"email is required"'
  $ python3 -c 'from api.problems import problem; print(problem(400, detail={"a":1})[2])'
  {"type": "about:blank", "title": "Bad Request", "status": "400", "detail": "{\"a\": 1}"}
  ```

### 4. `about:blank` responses get the title "Error" for most status codes (Medium)
- **File:** api/problems.py:7-13 (the `TITLES` table covers only 400, 404, 409, 422 and 500) and api/problems.py:19 (`TITLES.get(status, "Error")`).
- **RFC:** §4.2.1: "When "about:blank" is used, the title SHOULD be the same as the recommended HTTP status phrase for that code (e.g., "Not Found" for 404, and so on)".
- **Repro:**
  ```
  $ for c in 401 403 405 429 503; do python3 -c "from api.problems import problem; print(problem($c)[2])"; done
  {"type": "about:blank", "title": "Error", "status": "401"}
  {"type": "about:blank", "title": "Error", "status": "403"}
  {"type": "about:blank", "title": "Error", "status": "405"}
  {"type": "about:blank", "title": "Error", "status": "429"}
  {"type": "about:blank", "title": "Error", "status": "503"}
  ```
- **Related (Low):** `problem()` also accepts a custom title together with `about:blank`, which breaks the same SHOULD. Callers can do this, but the default code path does not.
  ```
  $ python3 -c 'from api.problems import problem; print(problem(404, title="Widget missing")[2])'
  {"type": "about:blank", "title": "Widget missing", "status": "404"}
  ```

### 5. The `type` URI changes with the request's host and scheme (Medium)
- **File:** api/problems.py:18 `urljoin(request_url, PROBLEM_BASE + type_)`
- **RFC:** §3.1.1: "Consumers MUST use the "type" URI (after resolution, if necessary) as the problem type's primary identifier." The same section says "it is RECOMMENDED that absolute URIs be used in "type" when possible". §4 says "New problem type definitions MUST document: 1. a type URI".
- **Effect:** one problem type ends up with several identifiers, one per host or scheme the request arrived on (prod, staging, localhost, http vs https). Consumers that match on `type` will see them as different problem types. A type URI should be a stable constant. Building it from `request_url` makes the identifier depend on the request.
- When `request_url=""` (the default) the result is the relative path `/problems/validation-error`. That follows the RFC's fallback advice ("when relative URIs are used, they include the full path"), so it is acceptable on its own. But passing `request_url` produces a different identifier for the same problem type.
- **Repro:**
  ```
  $ python3 -c 'from api.problems import validation_problem as v
  for u in ["", "https://api.example.com/users", "https://staging.example.com/a/b", "http://localhost:8000/x"]: print(repr(u), "->", __import__("json").loads(v([],request_url=u)[2])["type"])'
  '' -> /problems/validation-error
  'https://api.example.com/users' -> https://api.example.com/problems/validation-error
  'https://staging.example.com/a/b' -> https://staging.example.com/problems/validation-error
  'http://localhost:8000/x' -> http://localhost:8000/problems/validation-error
  ```

### 6. `type_` is not validated and can produce invalid or unintended type URIs (Low)
- **File:** api/problems.py:18
- **RFC:** §3.1.1: "The "type" member is a JSON string containing a URI reference [URI]". A value containing a space is not a valid URI reference. Dot-segments can also move the type outside `/problems/`.
- **Repro:**
  ```
  $ python3 -c 'from api.problems import problem; import json
  for t in ["//evil.example/x","https://evil.example/x","../admin","a b"]: print(repr(t),"->",json.loads(problem(400,type_=t,request_url="https://api.example.com/u")[2])["type"])'
  '//evil.example/x' -> https://api.example.com/problems///evil.example/x
  'https://evil.example/x' -> https://api.example.com/problems/https://evil.example/x
  '../admin' -> https://api.example.com/admin
  'a b' -> https://api.example.com/problems/a b
  ```
  You also cannot pass an absolute or `tag:` type URI. It always gets placed under `/problems/`. The only caller in the repo passes a fixed string, so this matters only for future callers.

### 7. Members are not type-checked and extensions can overwrite `type` (Low)
- **File:** api/problems.py:24-26 (`instance` is written unchecked; `doc.update(extensions)` runs last)
- **RFC:** §3.1.5: "The "instance" member is a JSON string containing a URI reference". §3.1 says consumers MUST ignore a member whose type is wrong. §3.2 describes extensions as "additional members", meaning not replacements for the standard ones.
- **Repro:**
  ```
  $ python3 -c 'from api.problems import problem; print(problem(404, instance=123)[2])'
  {"type": "about:blank", "title": "Not Found", "status": "404", "instance": 123}
  $ python3 -c 'from api.problems import problem; print(problem(404, **{"type":"x"})[2])'
  {"type": "x", "title": "Not Found", "status": "404"}
  ```
  (The other standard names cannot be overwritten this way. `status`, `title`, `detail` and `instance` are named parameters, so Python raises `TypeError: problem() got multiple values for argument 'status'`.)

### 8. Extension member names are not checked (Low, informational)
- **File:** api/problems.py:16, 26 (`**extensions`)
- **RFC:** §3.2: "their names SHOULD start with a letter ... SHOULD comprise characters from ALPHA, DIGIT ... and "_" ... and they SHOULD be three characters or longer."
- **Repro:**
  ```
  $ python3 -c 'from api.problems import problem; print(problem(400, **{"x":1, "my-field":2})[2])'
  {"type": "about:blank", "title": "Bad Request", "status": "400", "x": 1, "my-field": 2}
  ```
  The only extension used in the repo, `errors`, follows these rules.

## Checked and found conformant

- **Default type:** `type` defaults to `"about:blank"` when no `type_` is given (§3.1.1, §4.2.1). Checked with `problem(404)`.
- **Default titles:** for the statuses in `TITLES`, the `about:blank` title matches the HTTP reason phrase: 400 "Bad Request", 404 "Not Found", 409 "Conflict", 422 "Unprocessable Content" (RFC 9110 name), 500 "Internal Server Error".
- **HTTP status vs body status:** the HTTP status in the returned tuple has the same value as the body's `status` (§3.1.2 "Generators MUST use the same status code in the actual HTTP response"). Only the JSON type of the body field is wrong (finding 2).
- **Validation type URI:** `/problems/validation-error` with the default `request_url=""` is a relative reference with a full path, which is the RFC's fallback recommendation (§3.1.1).
- **`validation_problem` title:** it is a fixed string that does not vary between occurrences (§3.1.3 "SHOULD NOT change from occurrence to occurrence").
- **`errors` extension:** it is a valid extension name and has the same shape as the RFC's own validation example (§3.2). The RFC example's entries use `detail`/`pointer` members, while this code uses `field`/`msg`. The RFC does not require a particular shape, so this is not a nonconformance.
- **Body format:** the body is a JSON object, and `json.dumps` output is valid UTF-8-safe JSON (ASCII-escaped by default).

## Could not check / undetermined

- **Problem type documentation:** whether `/problems/validation-error` is documented as §4 requires ("MUST document: a type URI, a title, the HTTP status code"), and whether it resolves to HTML docs (§3.1.1/§3.2 SHOULD). There are no docs or routes for it in the repo.
- **HTTP framework wiring:** how the `(status, headers, body)` tuple reaches HTTP, for example whether a framework rewrites Content-Type, and whether content negotiation or Accept handling exists (§1, §3). There is no server code in the repo.
- **What callers pass as `message`/`detail`:** the §5 Security Considerations (no stack dumps or internals in `detail`) and the §3.1.4 "ought to focus on helping the client" guidance cannot be judged without callers.
- **`instance` usage:** no caller sets `instance`, so I cannot judge whether real values are absolute or full-path URIs (§3.1.5 RECOMMENDED).
- **Localization of `title`** (§3.1.3, §4.2.1 MAY) is not implemented. This is optional, not a nonconformance.
- **XML format (Appendix B):** not implemented. It is optional, so I did not assess it.
- **Compatibility (not an RFC issue):** `error_response` used to return `{"error": message}` on main. Existing clients that read `body["error"]` will break.
