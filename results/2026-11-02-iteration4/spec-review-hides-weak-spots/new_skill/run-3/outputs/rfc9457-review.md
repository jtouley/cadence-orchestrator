# RFC 9457 conformance review: main..feature/problem-details

Standard: RFC 9457 (text fetched from https://www.rfc-editor.org/rfc/rfc9457.txt, 838 lines). Brief: `.cadence/workstreams/problem-details-review.md` @ d588956.
Review only. Nothing was fixed, and no subagents were used.

## Scope and provenance

- `repo.bundle` verifies cleanly and has `main` = 7ae6e38 and `feature/problem-details` = 5efb782.
- **The local repo does not fully match the bundle.** Local `main` = 7ae6e38, which matches. Local `feature/problem-details` = 4aed654 ("eval setup"), which is one commit past the bundle's head. That commit only adds `.claude/**`, `.gitignore` and `repo.bundle` (`git diff --stat 5efb782 4aed654`). It does not touch `api/` or `tests/`. I left it out of scope as harness setup and reviewed the bundle's range, **main..5efb782**: `api/errors.py`, `api/problems.py`, `tests/test_problems.py`.
- All repro commands ran against a fresh clone of the bundle: `git clone -b feature/problem-details repo.bundle /tmp/rfcrev` (HEAD 5efb782), Python 3.13.18. The existing tests pass (`pytest -q` gives `2 passed`).

## Findings (most severe first)

### F1. `status` is serialized as a JSON string, not a JSON number. Severity: MUST-violation
- Location: `api/problems.py:20`, `"status": str(status),`
- RFC 9457 §3.1.2: "The "status" member is a JSON number indicating the HTTP status code". §3.1: "If a member's value type does not match the specified type, the member MUST be ignored -- i.e., processing will continue as if the member had not been present."
- Effect: the body breaks the member's type definition. Any conforming consumer is required to drop `status`, so in practice the advisory status is never delivered. The §3.1.2 "Generators MUST use the same status code in the actual HTTP response" requirement is met only in value: the HTTP status is the int 404 and the body holds the string "404".
- Repro:
  ```
  $ python3 -c 'import json; from api.problems import problem; s,h,b=problem(404); d=json.loads(b); print(repr(d["status"]), type(d["status"]).__name__, "http:", s, type(s).__name__)'
  '404' str http: 404 int
  ```

### F2. Responses use the `application/json` media type instead of `application/problem+json`. Severity: note (normative text, but no BCP 14 keyword); high practical impact
- Location: `api/problems.py:27`, `headers = {"Content-Type": "application/json"}`. Every `error_response` call goes through this via `api/errors.py:5`.
- RFC 9457 §1: "The data model for problem details is a JSON [JSON] object; when serialized as a JSON document, it uses the "application/problem+json" media type." The examples in §3 and the registration in §6.1 use it too.
- Effect: clients and generic tooling that detect problem details by media type, or that send `Accept: application/problem+json`, won't recognize these bodies as problem details.
- Repro:
  ```
  $ python3 -c 'from api.errors import error_response; print(error_response(404, "No such user"))'
  (404, {'Content-Type': 'application/json'}, '{"type": "about:blank", "title": "Not Found", "status": "404", "detail": "\\"No such user\\""}')
  ```

### F3. `detail` is JSON-encoded twice, so it isn't plain human-readable text. Severity: SHOULD-violation (indirect) / note
- Location: `api/problems.py:23`, `doc["detail"] = json.dumps(detail)`
- RFC 9457 §3.1.4: "The "detail" member is a JSON string containing a human-readable explanation specific to this occurrence of the problem." Also: "Consumers SHOULD NOT parse the "detail" member for information; extensions are more suitable and less error-prone ways to obtain such information."
- Effect: the value is still a JSON string, so the type is correct. But the text arrives wrapped in literal quote characters, and non-ASCII text arrives as literal `é` escapes. If `detail` is passed a dict or list, it is silently turned into a JSON-in-a-string blob. That pushes clients to parse `detail`, which the RFC says they SHOULD NOT do. Structured data belongs in extension members.
- Repro:
  ```
  $ python3 -c 'import json; from api.problems import problem; _,_,b=problem(400, detail="Café closed"); print(b); print(repr(json.loads(b)["detail"]))'
  {"type": "about:blank", "title": "Bad Request", "status": "400", "detail": "\"Caf\\u00e9 closed\""}
  '"Caf\\u00e9 closed"'
  $ python3 -c 'import json; from api.problems import problem; _,_,b=problem(400, detail={"field":"email"}); print(repr(json.loads(b)["detail"]))'
  '{"field": "email"}'
  ```

### F4. With `about:blank`, `title` falls back to "Error" instead of the status phrase. Severity: SHOULD-violation
- Location: `api/problems.py:7-13` (`TITLES` only covers 400/404/409/422/500) and `api/problems.py:19` (`TITLES.get(status, "Error")`).
- RFC 9457 §4.2.1: "When "about:blank" is used, the title SHOULD be the same as the recommended HTTP status phrase for that code (e.g., "Not Found" for 404, and so on)".
- Repro:
  ```
  $ python3 -c 'import json; from api.problems import problem
  for c in (401,403,405,415,429,503): print(c, json.loads(problem(c)[2])["title"])'
  401 Error
  403 Error
  405 Error
  415 Error
  429 Error
  503 Error
  ```
  (Python's `http.HTTPStatus(c).phrase` would supply the correct phrases.)

### F5. The `validation-error` problem type is not documented. Severity: MUST-violation (for a new problem type definition), based on what the range contains
- Location: `api/problems.py:31-39` (`validation_problem`, `type_="validation-error"`).
- RFC 9457 §4: "New problem type definitions MUST document: 1. a type URI ... 2. a title ... 3. the HTTP status code for it to be used with". Also: "A problem type URI SHOULD resolve to HTML [HTML5] documentation that explains how to resolve the problem." §3.1.1: "dereferencing it SHOULD provide human-readable documentation".
- Effect: the range defines a new type at `/problems/validation-error` but contains no documentation for it and no route serving `/problems/*`. The `errors` extension member is also undefined. Documentation outside this repo could exist, and I did not check deployed hosts.
- Repro:
  ```
  $ git ls-tree -r --name-only HEAD; git grep -n -i "validation-error\|problems/" HEAD -- . ':!api/problems.py' || echo "(no matches outside api/problems.py)"
  api/__init__.py
  api/errors.py
  api/problems.py
  tests/test_problems.py
  (no matches outside api/problems.py)
  ```

### F6. The `type` URI changes with the request's scheme and host, or is relative when `request_url` is empty. Severity: note (goes against a RECOMMENDED and weakens a consumer MUST)
- Location: `api/problems.py:18`, `urljoin(request_url, PROBLEM_BASE + type_)`. `request_url` defaults to `""` (`api/problems.py:16,31`).
- RFC 9457 §3.1.1: "Consumers MUST use the "type" URI (after resolution, if necessary) as the problem type's primary identifier." Also: "it is RECOMMENDED that absolute URIs be used in "type" when possible and that when relative URIs are used, they include the full path".
- Effect: one problem type gets several identifiers, depending on which host or scheme served the request (internal IPs, regional hosts, http vs https). With no `request_url`, the type is a relative full-path reference. The RFC permits that, but it's not the recommended absolute form. A related issue: an absolute `type_` argument produces a malformed type (R7 below).
- Repro:
  ```
  $ python3 -c 'import json; from api.problems import validation_problem
  for u in ("", "https://api.example.com/users", "http://10.0.0.5:8080/x", "https://eu.api.example.com/a/b"): print(repr(u), "->", json.loads(validation_problem([], request_url=u)[2])["type"])'
  '' -> /problems/validation-error
  'https://api.example.com/users' -> https://api.example.com/problems/validation-error
  'http://10.0.0.5:8080/x' -> http://10.0.0.5:8080/problems/validation-error
  'https://eu.api.example.com/a/b' -> https://eu.api.example.com/problems/validation-error
  $ python3 -c 'import json; from api.problems import problem; print(json.loads(problem(409, type_="https://example.com/probs/conflict", request_url="https://api.example.com/u")[2])["type"])'
  https://api.example.com/problems/https://example.com/probs/conflict
  ```

### F7. Extension kwargs can silently overwrite the core `type` member. Severity: note
- Location: `api/problems.py:26`, `doc.update(extensions)`. The core member is passed as `type_`, so a `type=` kwarg is accepted as an "extension".
- RFC 9457 §3.1/§3.2: `type` is a defined member with fixed semantics, and extensions are "additional members". Overwriting `type` this way yields a non-blank type that still carries the about:blank status-phrase title. Extension names are also not checked against the §4 naming SHOULDs ("SHOULD start with a letter ... SHOULD comprise characters from ALPHA, DIGIT ... and "_" ... SHOULD be three characters or longer"). `status=` raises a TypeError, so `status` can't be overwritten.
- Repro:
  ```
  $ python3 -c 'import json; from api.problems import problem; print(problem(404, type="https://evil.example/x", detail="d")[2])'
  {"type": "https://evil.example/x", "title": "Not Found", "status": "404", "detail": "\"d\""}
  $ python3 -c 'from api.problems import problem; problem(404, status=200)' 2>&1 | tail -1
  TypeError: problem() got multiple values for argument 'status'
  ```

### F8. The tests don't exercise the conformance points above. Severity: note
- Location: `tests/test_problems.py`. The tests check only `type == "about:blank"` and the `errors` extension. Nothing checks Content-Type, the JSON type of `status`, the content of `detail`, or titles. That's why F1–F4 pass CI (`2 passed`).

### Items checked and found conformant
- When `type_` is omitted, `type` defaults to `"about:blank"` (§3.1.1, §4.2.1).
- The HTTP status returned equals the `status` value (§3.1.2 MUST, value only; see F1 for the type).
- Titles for 400/404/409/422/500 match the RFC 9110 reason phrases, including "Unprocessable Content".
- `instance` is optional and omitted when None (§3.1.5).
- `validation_problem` uses a fixed title per type (§3.1.3 "SHOULD NOT change from occurrence to occurrence"), and its `errors` extension name meets the §4 naming SHOULDs.

## What I did not check
- The wire behaviour of a real HTTP server. The range has no server or framework, only `(status, headers, body)` tuples. I didn't verify how a framework would emit them, or whether it would override Content-Type or charset.
- Callers of `error_response` / `problem` outside this repo, or what text they pass as `detail`. That leaves the §5 Security Considerations on leaking information in `detail` unchecked.
- Whether `/problems/validation-error` is served or documented on any deployed host, or in docs outside the repo (relevant to F5).
- Content negotiation and `Accept` handling, plus localization of title/detail via `Accept-Language` (§1, §3.1.3, §4.2.1). Nothing in the range implements them.
- Appendix B (`application/problem+xml`) and Appendix C (embedding in other formats). Not implemented and optional.
- Validation of `instance` as a URI reference. It is passed through unchecked, and I didn't test malformed inputs.
- Consumer-side MUSTs (§3.1 ignore mismatched types, §3.2 ignore unknown extensions). This code only generates problem details.
- Backward compatibility with clients of the old `{"error": ...}` body that `api/errors.py` removed. It's outside RFC 9457, but the change is breaking.
- The commit 4aed654 ("eval setup") on the local branch, which is not in the bundle (see Scope).
