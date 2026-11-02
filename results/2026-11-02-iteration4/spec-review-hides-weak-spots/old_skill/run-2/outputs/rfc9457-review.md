# RFC 9457 conformance review: 7ae6e38..1e56777 (feature/problem-details)

Scope: `api/errors.py`, `api/problems.py`, `tests/test_problems.py` (`.claude/` tooling ignored; `.gitignore` and `repo.bundle` aren't relevant to RFC 9457).
Source: the RFC 9457 text, from https://www.rfc-editor.org/rfc/rfc9457.txt.
Environment: HEAD 1e5677746909a44c531ed705ee7c1d4d1a9c629d, Python 3.13.18. The existing tests pass (`python3 -m pytest -q tests` gives `2 passed`), but none of them check the issues below.

All repro commands are run from `/tmp/cr-run.jgTAI1HR/repo`.

## Nonconformances

### 1. "status" is a JSON string, not a JSON number (RFC 9457 Section 3.1.2, Section 3.1, Appendix A)
- Location: `api/problems.py:20` (`"status": str(status)`)
- RFC: "The "status" member is a JSON number indicating the HTTP status code". Section 3.1 says: "If a member's value type does not match the specified type, the member MUST be ignored". As a result, conforming consumers have to throw away every `status` this code produces. The Appendix A schema also declares `"type": "integer"`.
- Repro:
  ```
  python3 -c 'import json; from api.problems import problem; s,h,b=problem(404); d=json.loads(b); print(repr(d["status"]), type(d["status"]).__name__, s)'
  ```
  Output:
  ```
  '404' str 404
  ```

### 2. Content-Type is `application/json`, not `application/problem+json` (RFC 9457 Section 3, Section 1, Section 6)
- Location: `api/problems.py:27` (`headers = {"Content-Type": "application/json"}`). This affects every response, including those from `api/errors.py:5`.
- RFC Section 3: "When serialized in a JSON document, that format is identified with the "application/problem+json" media type." With the wrong media type, clients can't recognize the body as a problem details document.
- Repro:
  ```
  python3 -c 'from api.errors import error_response; print(error_response(404, "No user 42"))'
  ```
  Output:
  ```
  (404, {'Content-Type': 'application/json'}, '{"type": "about:blank", "title": "Not Found", "status": "404", "detail": "\\"No user 42\\""}')
  ```

### 3. "detail" is JSON-encoded twice, so it isn't plain human-readable text (RFC 9457 Section 3.1.4)
- Location: `api/problems.py:23` (`doc["detail"] = json.dumps(detail)`)
- RFC: "The "detail" member is a JSON string containing a human-readable explanation". The value is still a JSON string, so the type check passes. But the text inside it is a JSON literal: it is wrapped in literal quote characters, and non-ASCII characters are turned into `\uXXXX` escapes. Non-string inputs such as dicts become serialized JSON, which Section 3.1.4 says consumers SHOULD NOT parse. This affects every `error_response` call and `validation_problem`.
- Repro:
  ```
  python3 -c 'import json; from api.problems import problem; s,h,b=problem(400, detail="Name is required"); print(b); print(repr(json.loads(b)["detail"]))'
  python3 -c 'import json; from api.problems import problem; s,h,b=problem(400, detail="Café ünïcode"); print(repr(json.loads(b)["detail"]))'
  ```
  Output:
  ```
  {"type": "about:blank", "title": "Bad Request", "status": "400", "detail": "\"Name is required\""}
  '"Name is required"'
  '"Caf\\u00e9 \\u00fcn\\u00efcode"'
  ```

### 4. With about:blank, the title is not the HTTP status phrase for status codes outside TITLES (RFC 9457 Section 4.2.1, SHOULD)
- Location: `api/problems.py:7-13` (TITLES only covers 400/404/409/422/500) and `api/problems.py:19` (falls back to `"Error"`).
- RFC: "When "about:blank" is used, the title SHOULD be the same as the recommended HTTP status phrase for that code". Common codes such as 401, 403, 405, 429 and 503 all get the title "Error".
- Repro:
  ```
  python3 -c 'from api.problems import problem; print(problem(403)[2]); print(problem(401)[2]); print(problem(503)[2])'
  ```
  Output:
  ```
  {"type": "about:blank", "title": "Error", "status": "403"}
  {"type": "about:blank", "title": "Error", "status": "401"}
  {"type": "about:blank", "title": "Error", "status": "503"}
  ```

### 5. A custom title is accepted together with about:blank (RFC 9457 Section 4.2.1, SHOULD; Section 3.1.3)
- Location: `api/problems.py:19` (`title or ...` is applied even when `type_` is None)
- RFC: when about:blank is used, the title SHOULD be the status phrase. Passing a per-call title with no type also makes "title" vary between occurrences of the same problem type, which Section 3.1.3 says it SHOULD NOT. The API allows this, but nothing in the reviewed code calls it this way.
- Repro:
  ```
  python3 -c 'from api.problems import problem; print(problem(404, title="User missing")[2])'
  ```
  Output:
  ```
  {"type": "about:blank", "title": "User missing", "status": "404"}
  ```

## Lower-severity or conditional issues (not strict violations)

- **Extensions can overwrite the "type" member.** `api/problems.py:25`: `doc.update(extensions)` runs after the core members are set, and `type` isn't a named parameter. (`status`, `title`, `detail` and `instance` are named parameters, so passing them as kwargs binds the parameter instead.) A caller can therefore replace `type`, including with a non-string value, which would break Section 3.1.1. Repro: `python3 -c 'from api.problems import problem; print(problem(400, **{"type":"https://evil/x","title_":1})[2])'` gives `{"type": "https://evil/x", "title": "Bad Request", "status": "400", "title_": 1}`. No current caller does this.
- **Relative "type" when request_url is empty.** `api/problems.py:18`: `validation_problem` without a `request_url` gives `"type": "/problems/validation-error"`. This is allowed. Section 3.1.1 RECOMMENDS absolute URIs "when possible", and when relative URIs are used, that they include the full path, which this one does. So this is acceptable, but it differs from the absolute form produced when `request_url` is given. Repro: `python3 -c 'from api.problems import validation_problem as v; print(v([{"field":"email","msg":"required"}])[2])'` gives `{"type": "/problems/validation-error", ..., "status": "422", "detail": "\"One or more fields failed validation.\"", "errors": [...]}`. The output also shows issues 1 and 3.
- **`type_` is always treated as a slug.** Passing an absolute type URI produces a mangled URI: `problem(400, type_="https://example.com/probs/out-of-credit", request_url="https://api.example.com/a")` gives `"type": "https://api.example.com/problems/https://example.com/probs/out-of-credit"`. The result is still a syntactically valid URI reference, so this is not an RFC violation, but external or absolute problem types can't be used.

## Checked and found conformant

- **Section 3.1.1:** when no type is given, `type` is set to `"about:blank"` (`problems.py:18`; covered by `test_default_type_is_about_blank`).
- **Section 3.1.2:** the HTTP status returned is the same value as the `status` member, apart from the string/number type problem in issue 1 (`problems.py:28` returns `status`). `validation_problem` returns 422.
- **Section 4.2.1:** for statuses that are in TITLES, the about:blank title matches the status phrase. 404 gives "Not Found", and 422 gives "Unprocessable Content", which matches RFC 9110.
- **Section 3.1.5:** "instance" is only added when provided, and is passed through unchanged. Nothing in the reviewed code passes it.
- **Section 3.2 / Section 4:** the `errors` extension in `validation_problem` is a top-level member. Its name starts with a letter, uses only ALPHA characters and has at least 3 characters, so it meets the naming SHOULDs.
- **Optional members:** "detail" and "instance" are left out when they are None, which is allowed because all members are optional.
- **Section 3.1.1:** when `request_url` is supplied, the type is resolved to an absolute URI (for example `https://api.example.com/problems/validation-error`), which is the RECOMMENDED form.

## Could not check

- **Section 4 (MUST document a type URI, title and status) and the SHOULD that type URIs resolve to HTML documentation:** the repo has no documentation for the `validation-error` problem type and nothing that serves `/problems/...`. I can't tell whether it is documented somewhere outside this repo.
- **Language negotiation (Section 1, Accept-Language) and Accept handling:** the repo has no HTTP server or request layer. These functions return `(status, headers, body)` tuples and nothing in the repo turns them into HTTP responses. So I couldn't check end-to-end what goes over the wire, for example whether a framework later changes the Content-Type.
- **Section 5 (Security Considerations):** the content of `detail` comes from the callers of `error_response`, and no callers exist in the repo. I couldn't check whether internal details leak through it.
- **Appendix B (XML format):** no XML serialization is implemented.
