# RFC 9457 conformance review: main..feature/problem-details

- Repo: /tmp/cr-run.XgnD7cNy/repo, range `main..feature/problem-details` (commits b954349, 5efb782, 006f789)
- Standard: RFC 9457. Text fetched from https://www.rfc-editor.org/rfc/rfc9457.txt on 2026-11-02 (838 lines). Section numbers below are from that text.
- Workstream: `.cadence/workstreams/rfc9457-conformance.md` @ 41af36a (branch `orchestration`). Scope: RFC conformance only. Fixing code and style issues are out of scope.
- Files in scope: `api/problems.py` (new), `api/errors.py` (changed), `tests/test_problems.py` (new). Commit 006f789 ("eval setup") only adds `.claude/`, `.gitignore`, and `repo.bundle`. None of those are API code, so I didn't review them.
- Read-only: I made no edits or commits. Python ran with `PYTHONDONTWRITEBYTECODE=1` and pytest with `-p no:cacheprovider`. Afterwards, `git status --short` showed only `?? outputs/`.

All repros were run from the repo root like this: `cd /tmp/cr-run.XgnD7cNy/repo && PYTHONDONTWRITEBYTECODE=1 python3 -c '...'`. The outputs below are copied exactly from the terminal.

---

## Findings (most severe first)

### 1. The media type is `application/json`, not `application/problem+json`
- **RFC:** Section 3 says the JSON format "is identified with the "application/problem+json" media type". Every example in the RFC uses `Content-Type: application/problem+json`. Section 6 updates that media type registration.
- **Where:** `api/problems.py:27`, which has `headers = {"Content-Type": "application/json"}`. Every error goes through this line, including `api/errors.py:5`.
- **Impact:** Clients that check the media type won't recognize the body as Problem Details. Content negotiation, where a client lists `application/problem+json` in Accept, can't work.
- **Repro:**
  ```
  $ python3 -c 'from api.problems import problem; print(problem(404)[1])'
  {'Content-Type': 'application/json'}
  ```

### 2. `status` is a JSON string, not a JSON number
- **RFC:** Section 3.1.2 says "The "status" member is a JSON number". Section 3.1 says that if a member's value has the wrong type, it "MUST be ignored". So conforming consumers will throw away `status` in every response.
- **Where:** `api/problems.py:20`, which has `"status": str(status),`.
- **Repro:**
  ```
  $ python3 -c 'from api.problems import problem; import json; d=json.loads(problem(404)[2]); print(repr(d["status"]), type(d["status"]).__name__)'
  '404' str
  ```

### 3. `detail` is JSON-encoded twice, so it is not plain human-readable text
- **RFC:** Section 3.1.4 says `detail` is "a JSON string containing a human-readable explanation", and "Consumers SHOULD NOT parse the "detail" member for information; extensions are more suitable".
- **Where:** `api/problems.py:23`, which has `doc["detail"] = json.dumps(detail)`. Every `error_response` call reaches this line (`api/errors.py:5`), and so does `validation_problem` (`api/problems.py:36`).
- **Effect:** A string message comes out wrapped in literal quote characters. A non-string value (a dict or a number) is turned into JSON text inside `detail`. That pushes clients to parse `detail`, which is exactly the pattern the RFC tells consumers not to rely on. Strictly speaking the value is still a JSON string, but it isn't the human-readable explanation the RFC describes.
- **Repro:**
  ```
  $ python3 -c 'from api.errors import error_response; import json; s,h,b=error_response(404,"No user with id 42"); print(b); print(repr(json.loads(b)["detail"]))'
  {"type": "about:blank", "title": "Not Found", "status": "404", "detail": "\"No user with id 42\""}
  '"No user with id 42"'
  $ python3 -c 'from api.problems import problem; print(problem(400, detail={"field":"x"})[2])'
  {"type": "about:blank", "title": "Bad Request", "status": "400", "detail": "{\"field\": \"x\"}"}
  ```

### 4. With `about:blank`, `title` is often not the HTTP status phrase
- **RFC:** Section 4.2.1 says "When "about:blank" is used, the title SHOULD be the same as the recommended HTTP status phrase for that code (e.g., "Not Found" for 404 ...)".
- **Where:** `api/problems.py:7-13` and `:19`. `TITLES` only covers 400, 404, 409, 422 and 500. Every other status falls back to `"Error"`. Callers can also pass any `title` while `type` stays `about:blank`.
- **Repro (missing phrases):**
  ```
  $ python3 -c 'from api.problems import problem; import json; [print(c, json.loads(problem(c)[2])["title"]) for c in (401,403,405,415,429,503)]'
  401 Error
  403 Error
  405 Error
  415 Error
  429 Error
  503 Error
  ```
- **Repro (custom title on about:blank):**
  ```
  $ python3 -c 'from api.problems import problem; print(problem(404, title="Widget missing")[2])'
  {"type": "about:blank", "title": "Widget missing", "status": "404"}
  ```

### 5. The `type` URI depends on the request host, or is relative when no URL is given
- **RFC:** Section 3.1.1 says `type` is the problem type's "primary identifier", and that "it is RECOMMENDED that absolute URIs be used in "type" when possible". Section 4 says a new problem type definition "MUST document: 1. a type URI", meaning one stable identifier per problem type.
- **Where:** `api/problems.py:5` and `:18`, which has `urljoin(request_url, PROBLEM_BASE + type_)`. `api/errors.py:4` and `validation_problem` (`api/problems.py:31`) both default `request_url=""`.
- **Effect (a):** With the default `request_url`, `type` is a relative reference (`/problems/validation-error`). It has a full path, so it follows the fallback the RFC allows, but it goes against the RECOMMENDED absolute form.
- **Effect (b):** When `request_url` is passed, the same problem type gets a different identifier for each host, scheme or port the request came in on. Consumers that key on `type` will see three different problem types, and internal hostnames can leak into `type`. (The leak is a Section 5 Security Considerations concern.)
- **Repro:**
  ```
  $ python3 -c 'from api.problems import validation_problem; import json; print(json.loads(validation_problem([])[2])["type"])'
  /problems/validation-error
  $ python3 -c 'from api.problems import validation_problem; import json; [print(json.loads(validation_problem([],request_url=u)[2])["type"]) for u in ("https://api.example.com/users","https://eu.api.example.com/users","http://10.0.0.5:8080/users")]'
  https://api.example.com/problems/validation-error
  https://eu.api.example.com/problems/validation-error
  http://10.0.0.5:8080/problems/validation-error
  ```
- **Related:** `type_` is concatenated without escaping, so the result may not be a valid URI reference (Section 3.1.1 requires one):
  ```
  $ python3 -c 'from api.problems import problem; print(problem(400, type_="a b?c#d", request_url="https://x.test/")[2])'
  {"type": "https://x.test/problems/a b?c#d", "title": "Bad Request", "status": "400"}
  ```

### 6. Extension members can overwrite the standard members with values of the wrong type
- **RFC:** Section 3.1 defines the type of each standard member and says mismatches "MUST be ignored". Section 3.2 describes extensions as *additional* members.
- **Where:** `api/problems.py:26`, which has `doc.update(extensions)`. It runs after the standard members are set, so a `type=` or `detail=` keyword in `**extensions` replaces them. The `type_`/`type` naming makes this mistake easy to make.
- **Repro:**
  ```
  $ python3 -c 'from api.problems import problem; print(problem(404, type=123, title=None, detail="x", errors=1)[2])'
  {"type": 123, "title": "Not Found", "status": "404", "detail": "\"x\"", "errors": 1}
  $ python3 -c 'from api.problems import problem; print(problem(400, **{"type":"oops","detail":5})[2])'
  {"type": "oops", "title": "Bad Request", "status": "400", "detail": "5"}
  ```
  In the second case, `detail` is the raw integer `5` from the extensions dict. It replaced the encoded string, so its type is wrong under Section 3.1.4.

### 7. For a custom problem type, `title` defaults to the status phrase (low)
- **RFC:** Section 3.1.3 says `title` is a "summary of the problem type". Section 4 says a new type MUST document "a title that appropriately describes it".
- **Where:** `api/problems.py:19`. With a custom `type_` and no `title`, the title becomes the generic status phrase.
- **Repro:**
  ```
  $ python3 -c 'from api.problems import problem; print(problem(500, type_="db-down")[2])'
  {"type": "/problems/db-down", "title": "Internal Server Error", "status": "500"}
  ```

### 8. Extension member names are not checked (low, advisory)
- **RFC:** Section 4 says extension names "SHOULD start with a letter ... SHOULD comprise characters from ALPHA, DIGIT ... and "_" ... SHOULD be three characters or longer". Section 3.2 adds that names must fit the XML Name rule to be usable in the XML format.
- **Where:** `api/problems.py:16` (`**extensions`) and `:26`. Any name is accepted.
- **Repro:**
  ```
  $ python3 -c 'from api.problems import problem; print(problem(400, **{"x":1, "trace-id":"abc", "1st":2})[2])'
  {"type": "about:blank", "title": "Bad Request", "status": "400", "x": 1, "trace-id": "abc", "1st": 2}
  ```

### 9. `instance` is not checked as a URI reference (low)
- **RFC:** Section 3.1.5 says `instance` is "a JSON string containing a URI reference". Section 3.1.5 also RECOMMENDS absolute URIs.
- **Where:** `api/problems.py:24-25`. The value is passed through unchanged. No code in the range sets `instance`, so this only matters for future callers.
- **Repro:**
  ```
  $ python3 -c 'from api.problems import problem; print(problem(400, instance="not a uri ref <>")[2])'
  {"type": "about:blank", "title": "Bad Request", "status": "400", "instance": "not a uri ref <>"}
  ```

---

## Checked and conforming
- **Body status matches the HTTP status (Section 3.1.2 MUST):** `problem()` returns the same `status` it writes into the body, apart from the string type in Finding 2.
- **Default type (Section 3.1.1 / 4.2.1):** `type` defaults to `about:blank`. Tested by `test_default_type_is_about_blank`.
- **Validation errors:** `validation_problem` uses 422 and an `errors` extension, which matches the shape of the RFC Section 3 example. The item keys are `field`/`msg` rather than the example's `detail`/`pointer`. That is not a conformance issue, because the example is non-normative.
- **Existing tests:** `python3 -m pytest -q -p no:cacheprovider tests` printed `2 passed in 0.01s`. The tests don't assert the Content-Type, the type of `status`, or the contents of `detail`, so none of Findings 1-3 are covered.
- **Field name (`api/errors.py`):** the old `{"error": message}` field was removed. That is a breaking change for existing clients, but it is outside the RFC scope.

## What I did not check
- **HTTP layer:** there is no HTTP server, router or framework in the repo. `problem()` returns a `(status, headers, body)` tuple. I couldn't test how responses are actually sent: Accept / content negotiation (Section 4, and Section 12.5.1 of RFC 9110), `Content-Language`, or whether something downstream rewrites the Content-Type.
- **Call sites:** the only caller of `error_response` / `validation_problem` is the test file. I couldn't confirm what `detail`, `title` or extension values real code passes. Section 5 (leaking internals through `detail`) needs real callers to judge.
- **Type URIs:** `/problems/*` has no endpoint or documentation in the repo, so I couldn't verify Section 3.1.1 / 4 ("dereferencing it SHOULD provide human-readable documentation") or the MUST in Section 4 that each new type document its URI, title and status code.
- **XML format (Appendix B, `application/problem+xml`):** not implemented and not checked.
- **Localization of `title` (Sections 3.1.3, 4.2.1):** not checked.
- **Unrelated files:** `.claude/**`, `repo.bundle` and `.gitignore`, added in commit 006f789, were not reviewed because they aren't API code.
- **HTTP problem types registry (Section 4.2):** no registered types other than `about:blank` are used, so I didn't check registry entries.
