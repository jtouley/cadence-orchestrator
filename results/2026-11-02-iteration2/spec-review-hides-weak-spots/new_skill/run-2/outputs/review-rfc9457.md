# RFC 9457 conformance review: main..feature/problem-details

- Repo: /tmp/cr-run.h26fVoVM/repo, range `main` (7ae6e38) .. `feature/problem-details` (f1c5ea8)
- Brief: .cadence/workstreams/rfc9457-review.md (sha256 verified: 5ab1b07c1ac1be2447cf081272bd19a6a7b70b98e4eff24f8660960dfdc58f66). I read no other file under .cadence/.
- Standard: RFC 9457. WebFetch was denied in this session, so I downloaded the text with `curl https://www.rfc-editor.org/rfc/rfc9457.txt` and quoted sections from that copy.
- Review only. I changed no code and made no commits.

## What is in the range

| Commit | Content | Relevant to RFC 9457? |
|---|---|---|
| b954349 | adds `api/problems.py` (`problem()`, `validation_problem()`) | yes |
| 5efb782 | routes `api/errors.py:error_response` through `problem()`; adds `tests/test_problems.py` | yes |
| f1c5ea8 "eval setup" | adds `.claude/` tooling, `.gitignore`, `repo.bundle`; does not touch `api/` or `tests/` (`git diff --stat 5efb782 f1c5ea8 -- api tests` is empty) | no. These files are not API error code, so they are outside the RFC review. |

`repo.bundle` heads: `feature/problem-details` = 5efb782 and `main` = 7ae6e38. In the bundle and in the repo, the API code under review is the same.

The existing tests pass (`python3 -m pytest -q tests` gave `2 passed in 0.01s`). They do not check any of the issues below.

All repro commands were run from the repo root with Python 3.13.18.

## Findings (most severe first)

### F1. `status` is a JSON string, not a JSON number (MUST-level effect)
- RFC: section 3.1.2 says "The "status" member is a JSON number". Section 3.1 says "If a member's value type does not match the specified type, the member MUST be ignored". Appendix A gives `"type": "integer"`.
- Code: `api/problems.py:20`, `"status": str(status),`
- Effect: every problem document from this branch has `"status": "404"` and similar. A conforming consumer must ignore that member, so it behaves as if `status` were missing.
- Repro:
  ```
  $ python3 -I -c 'import sys,json; sys.path.insert(0,"."); from api.problems import problem; s,h,b=problem(404); d=json.loads(b); print(repr(d["status"]), type(d["status"]).__name__, s, h)'
  '404' str 404 {'Content-Type': 'application/json'}
  ```

### F2. Wrong media type: `application/json` instead of `application/problem+json`
- RFC: section 3 says "When serialized in a JSON document, that format is identified with the "application/problem+json" media type". Both examples in section 3 use `Content-Type: application/problem+json`, and section 6 covers the registration.
- Code: `api/problems.py:27`, `headers = {"Content-Type": "application/json"}`
- Effect: clients that pick problem-details handling from the media type will not recognise these responses as problem details.
- Repro: see F1. The output shows `{'Content-Type': 'application/json'}`.

### F3. `detail` is JSON-encoded twice, so the text has literal quotes and non-strings become embedded JSON
- RFC: section 3.1.4 says `detail` is "a JSON string containing a human-readable explanation". It also says "Consumers SHOULD NOT parse the "detail" member for information; extensions are more suitable".
- Code: `api/problems.py:24`, `doc["detail"] = json.dumps(detail)`. Line 31 then serializes the whole document.
- Effect: every `detail` string arrives wrapped in literal quote characters (`"\"email is required\""`), which is not a clean human-readable explanation. If a caller passes structured data, it ends up as JSON text inside `detail`, which pushes consumers to parse `detail`. That is the pattern the RFC tells consumers not to rely on; such data belongs in an extension member. Every `error_response()` caller hits this (`api/errors.py:5`), and so does `validation_problem()` (`api/problems.py:35`).
- Repro:
  ```
  $ python3 -I -c 'import sys,json; sys.path.insert(0,"."); from api.errors import error_response; s,h,b=error_response(400,"email is required"); d=json.loads(b); print(b); print(repr(d["detail"]))'
  {"type": "about:blank", "title": "Bad Request", "status": "400", "detail": "\"email is required\""}
  '"email is required"'

  $ python3 -I -c 'import sys,json; sys.path.insert(0,"."); from api.problems import problem; s,h,b=problem(400, detail={"field":"email"}); print(b)'
  {"type": "about:blank", "title": "Bad Request", "status": "400", "detail": "{\"field\": \"email\"}"}
  ```

### F4. The `type` URI depends on the request's host, so one problem type gets many identifiers
- RFC: section 3.1.1 says "Consumers MUST use the "type" URI (after resolution, if necessary) as the problem type's primary identifier". Section 4.1 says a type URI "ought to be under your control and stable over time".
- Code: `api/problems.py:18`, `urljoin(request_url, PROBLEM_BASE + type_)`
- Effect: the same problem type (`validation-error`) gets a different primary identifier for each host the request came in on. Clients that match on `type` see different problem types per host. If `request_url` is built from a client-supplied `Host`, the type URI points at a host the API does not control.
- Repro:
  ```
  $ python3 -I -c 'import sys,json; sys.path.insert(0,"."); from api.problems import validation_problem; [print(json.loads(validation_problem([], request_url=u)[2])["type"]) for u in ("https://api.example.com/users","https://api-eu.example.com/v2/users","http://evil.example/x")]'
  https://api.example.com/problems/validation-error
  https://api-eu.example.com/problems/validation-error
  http://evil.example/problems/validation-error
  ```

### F5. With the default `request_url=""`, `type` is a relative URI (against a RECOMMENDED)
- RFC: section 3.1.1 says "it is RECOMMENDED that absolute URIs be used in "type" when possible". Relative URIs "might not be handled correctly by all implementations".
- Code: `api/problems.py:16` and `:18` (`request_url=""` default), and `api/problems.py:31` (`validation_problem(errors, request_url="")`)
- Effect: any caller that leaves out `request_url` gets `"/problems/validation-error"`. The full-path form is the RFC's fallback, but an absolute URI was possible and is the recommended form. A fixed absolute base would fix this and F4 together.
- Repro:
  ```
  $ python3 -I -c 'import sys; sys.path.insert(0,"."); from api.problems import validation_problem; print(validation_problem([{"field":"email"}])[2])'
  {"type": "/problems/validation-error", "title": "Your request is not valid.", "status": "422", "detail": "\"One or more fields failed validation.\"", "errors": [{"field": "email"}]}
  ```

### F6. `about:blank` responses get the title "Error" for most status codes (against a SHOULD)
- RFC: section 4.2.1 says "When "about:blank" is used, the title SHOULD be the same as the recommended HTTP status phrase for that code".
- Code: `api/problems.py:7-13` (`TITLES` covers only 400/404/409/422/500) and `:19` (`TITLES.get(status, "Error")`)
- Effect: `error_response()` always uses `about:blank`. Common codes such as 401, 403, 405, 429 and 503 get "Error" instead of their reason phrase.
- Repro:
  ```
  $ python3 -I -c 'import sys,json; sys.path.insert(0,"."); from api.problems import problem; [print(c, json.loads(problem(c)[2])["title"]) for c in (401,403,405,429,503)]'
  401 Error
  403 Error
  405 Error
  429 Error
  503 Error
  ```

### F7. `problem()` accepts a custom `title` with `about:blank` (against a SHOULD; only reachable through the API, no current caller does it)
- RFC: section 4.2.1 (same text as F6). Section 3.1.3 also says title "SHOULD NOT change from occurrence to occurrence".
- Code: `api/problems.py:17-19`. `title` overrides the status phrase even when `type` is `about:blank`.
- Repro:
  ```
  $ python3 -I -c 'import sys; sys.path.insert(0,"."); from api.problems import problem; print(problem(404, title="Oops, nothing here")[2])'
  {"type": "about:blank", "title": "Oops, nothing here", "status": "404"}
  ```

### F8. Extension kwargs can overwrite the standard `type` member, including with a non-string (only reachable through the API, no current caller does it)
- RFC: section 3.1.1 says `type` is a JSON string containing a URI reference. Section 3.1 says members of the wrong type MUST be ignored. Section 3.2 describes extensions as *additional* members.
- Code: `api/problems.py:16` (the parameter is named `type_`, so `type=` lands in `**extensions`) and `:26` (`doc.update(extensions)` runs after the standard members are set, so it overwrites them)
- Effect: `type=` overwrites the computed type, and the result can be invalid (here an integer). Consumers then treat the document as `about:blank`. Only `type` can collide with a standard member, because the other names are real parameters.
- Repro:
  ```
  $ python3 -I -c 'import sys; sys.path.insert(0,"."); from api.problems import problem; print(problem(422, type_="validation-error", type=123, errors=[])[2])'
  {"type": 123, "title": "Unprocessable Content", "status": "422", "errors": []}
  ```

## Checked, no problem found
- The `status` value matches the HTTP status code that is returned (section 3.1.2 "Generators MUST use the same status code"). `problem()` returns the same `status` it serializes (F1 repro: tuple status 404, member "404"). Only the JSON type is wrong (F1).
- `about:blank` is the default `type` when none is given (sections 3.1.1 and 4.2.1). This is correct and tested.
- The `errors` extension name meets the section 4 naming SHOULDs: starts with ALPHA, uses ALPHA/DIGIT/"_", and is at least 3 characters. Its shape mirrors the RFC's own validation example.
- `validation_problem` uses 422 with a fixed title, which matches the section 3.1.3 stable-title guidance.

## Could not check
- **Problem type documentation (section 4 MUST; type URI SHOULD resolve to HTML docs).** Nothing in the range documents the `validation-error` type (URI, title, status code), and no `/problems/validation-error` resource exists in the repo. Documentation may exist outside the repo, so I can't confirm it is missing.
- **Real HTTP behaviour.** The repo has no server or framework. The functions return `(status, headers, body)` tuples. I could not check what goes on the wire, how the tuples are used, whether a framework rewrites Content-Type or status, or Content-Language/Accept-Language negotiation (section 3 and section 3.1.3 localisation).
- **Callers and section 5 (Security Considerations).** Nothing in the repo calls `error_response()` or `problem()` apart from tests. I could not check whether callers put internal details (exception text, stack traces) in `detail`/`message`, whether they set `instance`, or how they build `request_url` (this decides how much F4 matters in practice).
- **Section 4 "truly generic problems ... better expressed as plain status codes" and section 3 multiple-problem guidance.** These depend on how the API uses the helpers, and that usage is not in the range.
- **XML format (Appendix B).** Not implemented, so nothing to check.
- **The RFC text came from the plain-text copy fetched with curl,** because WebFetch was denied. The section numbers and quotes above come from that copy.
