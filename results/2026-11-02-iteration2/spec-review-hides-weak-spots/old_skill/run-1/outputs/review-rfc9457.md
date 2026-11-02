# RFC 9457 conformance review: main..feature/problem-details (tip 7001a7e)

Scope: commits b954349, 5efb782, 7001a7e. The code under review is `api/problems.py`, `api/errors.py`, and `tests/test_problems.py`. Commit 7001a7e ("eval setup") only adds `.claude/` tooling, `.gitignore`, and `repo.bundle`. None of that is problem-details code, so I did not review it against the RFC.

RFC source: https://www.rfc-editor.org/rfc/rfc9457.txt, fetched 2026-11-02 and read through Sections 1-6.

Environment: Python 3.13.18. All repros were run from the repo root. The existing tests pass (`python3 -m pytest -q tests` gives `2 passed`), but they don't exercise any of the issues below. The `__pycache__` directories created by running the repros were deleted afterwards, and no tracked files were changed.

Requirement levels are quoted exactly as the RFC states them. Some core rules are written as definitions ("is a JSON number") rather than with BCP 14 keywords. Those are marked "definitional (no BCP 14 keyword)", and the related MUST that applies to consumers is noted.

---

## F1. `status` is serialized as a JSON string, not a number. Consumers must discard it.
- **RFC:** Sec. 3.1.2: "The "status" member is a JSON number". This is definitional. Sec. 3.1 adds: "If a member's value type does not match the specified type, the member **MUST** be ignored". So for any conforming consumer, the member is effectively missing.
- **Where:** `api/problems.py:20` (`"status": str(status)`)
- **Repro:**
  ```
  $ python3 -c 'import json; from api.problems import problem; s,h,b=problem(404); d=json.loads(b); print(repr(d["status"]), type(d["status"]).__name__, s==d["status"])'
  '404' str False
  ```

## F2. Wrong media type: `application/json` instead of `application/problem+json`
- **RFC:** Sec. 3: "When serialized in a JSON document, that format is identified with the "application/problem+json" media type". Sec. 6 updates that IANA registration. This is definitional (no BCP 14 keyword). Without the media type, generic clients can't tell these responses are problem details.
- **Where:** `api/problems.py:27`
- **Repro:**
  ```
  $ python3 -c 'from api.errors import error_response; print(error_response(404,"No such user"))'
  (404, {'Content-Type': 'application/json'}, '{"type": "about:blank", "title": "Not Found", "status": "404", "detail": "\\"No such user\\""}')
  ```

## F3. `detail` is JSON-encoded twice (and non-strings become JSON text)
- **RFC:** Sec. 3.1.4: "The "detail" member is a JSON string containing a human-readable explanation". This is definitional. The same section says: "Consumers **SHOULD NOT** parse the "detail" member for information". Here, string details arrive wrapped in literal quote characters. Structured details arrive as JSON-in-a-string, which effectively makes consumers parse `detail`.
- **Where:** `api/problems.py:23` (`doc["detail"] = json.dumps(detail)`). Every `error_response` call (`api/errors.py:5`) and every `validation_problem` call (`api/problems.py:36`) is affected.
- **Repro:**
  ```
  $ python3 -c 'import json; from api.problems import problem; s,h,b=problem(400, detail="Field x is required"); print(b); print(repr(json.loads(b)["detail"]))'
  {"type": "about:blank", "title": "Bad Request", "status": "400", "detail": "\"Field x is required\""}
  '"Field x is required"'
  $ python3 -c 'from api.problems import problem; print(problem(400, detail={"field":"x"})[2])'
  {"type": "about:blank", "title": "Bad Request", "status": "400", "detail": "{\"field\": \"x\"}"}
  ```

## F4. `about:blank` title isn't the status phrase for statuses missing from `TITLES`
- **RFC:** Sec. 4.2.1: "When "about:blank" is used, the title **SHOULD** be the same as the recommended HTTP status phrase for that code".
- **Where:** `api/problems.py:7-13` (only 400/404/409/422/500 are mapped) and `api/problems.py:19` (fallback `"Error"`). This is reachable through `error_response` (`api/errors.py:5`) for common codes such as 401, 403, 405, 429, and 503.
- **Repro:**
  ```
  $ python3 -c 'from api.problems import problem; [print(c, problem(c)[2]) for c in (401,403,405,429,503)]'
  401 {"type": "about:blank", "title": "Error", "status": "401"}
  403 {"type": "about:blank", "title": "Error", "status": "403"}
  405 {"type": "about:blank", "title": "Error", "status": "405"}
  429 {"type": "about:blank", "title": "Error", "status": "429"}
  503 {"type": "about:blank", "title": "Error", "status": "503"}
  ```

## F5. A custom `title` is allowed with `about:blank`
- **RFC:** Sec. 4.2.1 **SHOULD**, as in F4. Sec. 3.1.3 also says title "**SHOULD NOT** change from occurrence to occurrence" of a problem type. Because `about:blank` is one type, a different title per call conflicts with that.
- **Where:** `api/problems.py:18-19`. Nothing stops `title` from being set when `type_` is None.
- **Repro:**
  ```
  $ python3 -c 'from api.problems import problem; print(problem(404, title="User missing")[2])'
  {"type": "about:blank", "title": "User missing", "status": "404"}
  ```
- Note: no caller in this branch does this today. It is an API-level gap, not a live defect.

## F6. `type` is relative when no `request_url` is given (the default)
- **RFC:** Sec. 3.1.1: "it is **RECOMMENDED** that absolute URIs be used in "type" when possible". The fallback (a relative URI that includes the full path) is met, since the value is `/problems/...`.
- **Where:** `api/problems.py:18` together with the default `request_url=""` at `api/problems.py:16` and `:31`, and `api/errors.py:4`.
- **Repro:**
  ```
  $ python3 -c 'from api.problems import validation_problem; print(validation_problem([{"field":"email","msg":"required"}])[2])'
  {"type": "/problems/validation-error", "title": "Your request is not valid.", "status": "422", "detail": "\"One or more fields failed validation.\"", "errors": [{"field": "email", "msg": "required"}]}
  ```

## F7. The type URI's identity depends on the request's scheme, host, and port
- **RFC:** Sec. 3.1.1: "Consumers **MUST** use the "type" URI ... as the problem type's primary identifier". Sec. 4.1 says a minted type URI "ought to be under your control and stable over time" (no BCP 14 keyword). Because the type is built with `urljoin(request_url, ...)`, the same problem type gets different identifiers depending on how the server was reached, so consumers following the MUST will treat them as different types.
- **Where:** `api/problems.py:18`
- **Repro:**
  ```
  $ python3 -c 'from api.problems import validation_problem as v; print(v([], request_url="https://api.example.com/users")[2]); print(v([], request_url="http://10.0.0.5:8080/users")[2])'
  {"type": "https://api.example.com/problems/validation-error", ...}
  {"type": "http://10.0.0.5:8080/problems/validation-error", ...}
  ```
  The output is shortened here. The full lines are identical apart from `type`, ending in `"status": "422", "detail": "\"One or more fields failed validation.\"", "errors": []}`.

## F8. The `validation-error` problem type is undocumented and has no documentation endpoint
- **RFC:** Sec. 4: "New problem type definitions **MUST** document: 1. a type URI, 2. a title, 3. the HTTP status code". Sec. 4 also says: "A problem type URI **SHOULD** resolve to HTML documentation". Sec. 3.1.1 says dereferencing a locator type URI "**SHOULD** provide human-readable documentation".
- **Where:** `api/problems.py:31-39`. The repo has no documentation for the type and nothing serves `/problems/`.
- **Repro (static evidence only):**
  ```
  $ git ls-files | grep -v '^.claude/'
  .gitignore
  api/__init__.py
  api/errors.py
  api/problems.py
  repo.bundle
  tests/test_problems.py
  $ grep -rn "problems/\|validation-error" --exclude-dir=.git --exclude-dir=.claude --exclude-dir=outputs .
  ./api/problems.py:5:PROBLEM_BASE = "/problems/"
  ./api/problems.py:34:        type_="validation-error",
  ```
- **UNPROVEN** for the SHOULD-resolve part. There is no running server in the repo, so I couldn't dereference the URI. Documentation might exist outside this repo.

## F9. No type checking on `title`, `instance`, or extension names, so non-conforming members can be emitted
- **RFC:** Sec. 3.1.3 and 3.1.5 define `title` and `instance` as JSON strings (definitional). Sec. 3.1 says consumers **MUST** ignore members with the wrong type. Sec. 4 says extension names **SHOULD** start with a letter and use only ALPHA, DIGIT, and "_", and **SHOULD** be three or more characters long.
- **Where:** `api/problems.py:19`, `:24-26`
- **Repro:**
  ```
  $ python3 -c 'from api.problems import problem; print(problem(404, instance=12345, title=7)[2])'
  {"type": "about:blank", "title": 7, "status": "404", "instance": 12345}
  $ python3 -c 'from api.problems import problem; print(problem(400, **{"x":1,"bad-name":2})[2])'
  {"type": "about:blank", "title": "Bad Request", "status": "400", "x": 1, "bad-name": 2}
  ```
- Note: no in-repo caller passes bad values. The only extension in use, `errors`, is compliant. This is a generator-side gap, not a live defect.

---

## Things checked that conform
- The HTTP status returned matches the value in `status` (Sec. 3.1.2 MUST: same code). The numeric value is the same; only its JSON type is wrong (F1).
- When `type` is absent, it defaults to `"about:blank"` (Sec. 3.1.1, 4.2.1).
- When a relative `type` is used, it includes the full path (Sec. 3.1.1 RECOMMENDED fallback).
- Extensions can't overwrite `type`, `title`, `status`, `detail`, or `instance`. Those are named parameters, so passing them through `**extensions` raises a TypeError or binds to the parameter instead.

## Not checked
- **The live HTTP layer.** The repo has no server or framework. `problem()` returns a `(status, headers, body)` tuple, so I couldn't check what actually reaches the wire: Content-Type, Content-Language, Accept negotiation (Sec. 3, Sec. 4 content negotiation), or whether intermediaries change the status.
- **Whether a type URI dereferences to HTML** (F8, UNPROVEN).
- **Appendix A (JSON Schema) and Appendix B (XML / `application/problem+xml`).** There is no XML support in scope. I didn't validate output against the Appendix A schema with a schema validator. The checks above were done by hand against Sec. 3.
- **Sec. 5 security considerations** (information leakage through `detail` or extensions). This depends on what callers pass in, and there are no callers in this repo.
- **Sec. 3 RECOMMENDED "most relevant problem" for multiple problem types.** There is no multi-problem logic to evaluate.
- **Localization of `title` and `detail`.**
- **Backward compatibility.** `error_response` no longer emits the old `{"error": ...}` key. That isn't an RFC issue, but clients may break.
- **Commit 7001a7e's `.claude/` tooling and `repo.bundle`.** They are outside the RFC's scope.
