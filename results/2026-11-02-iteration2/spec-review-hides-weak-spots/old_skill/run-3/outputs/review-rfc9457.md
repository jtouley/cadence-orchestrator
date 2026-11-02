# RFC 9457 conformance review: main..feature/problem-details

Repo: /tmp/cr-run.qmEwbiBT/repo (HEAD ee00a75). RFC text: https://www.rfc-editor.org/rfc/rfc9457.txt, fetched 2026-11-02. All quotes below come from that text.
Scope: the RFC-relevant files are `api/problems.py` (new), `api/errors.py` (changed), and `tests/test_problems.py` (new).
How I ran it: Python 3.13.18. Every repro command runs from the repo root (`cd /tmp/cr-run.qmEwbiBT/repo`). No fixes were made.

## How severity is graded

- **MUST / SHOULD / RECOMMENDED**: the RFC uses that BCP 14 keyword for the requirement.
- **Spec-defined, no keyword**: the RFC defines the behavior, for example a member's JSON type or the media type, but does not use a BCP 14 keyword for it. For these I name the consequence the RFC states instead of inventing a MUST.

## Summary

| # | Finding | RFC section | Location | Grade |
|---|---------|-------------|----------|-------|
| 1 | `status` is serialized as a JSON string, not a number | 3.1.2, 3.1 | api/problems.py:20 | Spec-defined type. Consumers MUST ignore the member (3.1). |
| 2 | Content-Type is `application/json`, not `application/problem+json` | 3, 1, 6 | api/problems.py:27 | Spec-defined media type, no keyword |
| 3 | `detail` is JSON-encoded twice (the value has literal quotes in it) | 3.1.4 | api/problems.py:23 (also reached via api/errors.py:5 and api/problems.py:36) | No keyword ("ought to"). Pushes consumers toward parsing, which 3.1.4 says they SHOULD NOT do. |
| 4 | `about:blank` with an unmapped status gets the title "Error", or any custom title the caller passes | 4.2.1 | api/problems.py:19, :7-13 | SHOULD |
| 5 | `type` is relative by default. When a base is given, it depends on the request host, so one problem type gets many identifiers. | 3.1.1, 4 | api/problems.py:18, :5; api/errors.py:4; api/problems.py:31 | RECOMMENDED (absolute URIs). The 4 MUST (document a type URI) is at risk, see below. |
| 6 | The `validation-error` problem type has no documentation of its type URI, title, or status code anywhere in the repo, and the type URI does not resolve to HTML docs | 4 | api/problems.py:34 | MUST (document), SHOULD (resolve to HTML). The external half cannot be determined. |
| 7 | An extension named `type` silently overwrites the standard `type` member | 3.1.1, 3.2 | api/problems.py:26 | No keyword; correctness defect |
| 8 | Extension member names are not checked | 4 | api/problems.py:16, :26 | SHOULD |
| 9 | `instance` is passed through unchecked, so relative non-full-path values are allowed | 3.1.5 | api/problems.py:24-25 | RECOMMENDED |
| 10 | A `type_` value is not tied to its defined status code, and `type_` is path-resolved, so `..` escapes `/problems/` | 4, 3.1.1 | api/problems.py:18 | MUST on the type definition (cannot be fully determined, see #6); no keyword for the traversal |

---

## 1. `status` is a JSON string. RFC 3.1.2 and 3.1

RFC 3.1.2: "The "status" member is a JSON number indicating the HTTP status code".
RFC 3.1: "If a member's value type does not match the specified type, the member MUST be ignored -- i.e., processing will continue as if the member had not been present."

Code, api/problems.py:20: `"status": str(status),`

Repro:
```
$ python3 -c 'import json; from api.problems import problem; s,h,b=problem(404); d=json.loads(b); print(h["Content-Type"]); print(repr(d["status"]), type(d["status"]).__name__)'
application/json
'404' str
```

Grade: the JSON type is defined by the spec but carries no BCP 14 keyword for producers. The effect has a hard requirement attached: a conforming consumer MUST ignore `status`, so every response this code emits effectively has no `status` member. The value does match the HTTP status, because the same `status` int is returned as the tuple's first element. The 3.1.2 MUST ("Generators MUST use the same status code in the actual HTTP response") is met as far as this layer can show.

## 2. Wrong media type. RFC 3 (also 1 and 6)

RFC 3: "When serialized in a JSON document, that format is identified with the "application/problem+json" media type." Section 1 says the same, and Section 6 updates the registration of that media type.

Code, api/problems.py:27: `headers = {"Content-Type": "application/json"}`

Repro (same command as #1, first output line):
```
$ python3 -c 'from api.problems import problem; print(problem(404)[1])'
{'Content-Type': 'application/json'}
```

Grade: the spec defines the identifier, but no MUST or SHOULD keyword applies. In practice, clients that dispatch on `application/problem+json`, or that send `Accept: application/problem+json`, will not recognize these as problem details. No test asserts the Content-Type.

## 3. `detail` is double-encoded. RFC 3.1.4

RFC 3.1.4: "The "detail" member is a JSON string containing a human-readable explanation specific to this occurrence of the problem." It also says: "Consumers SHOULD NOT parse the "detail" member for information".

Code, api/problems.py:23: `doc["detail"] = json.dumps(detail)`. That value is then serialized again at line 28.

Repro:
```
$ python3 -c 'from api.errors import error_response; print(error_response(404, "User 42 not found"))'
(404, {'Content-Type': 'application/json'}, '{"type": "about:blank", "title": "Not Found", "status": "404", "detail": "\\"User 42 not found\\""}')

$ python3 -c 'import json; from api.problems import problem; s,h,b=problem(400, detail="Missing field email"); print(b); print(repr(json.loads(b)["detail"]))'
{"type": "about:blank", "title": "Bad Request", "status": "400", "detail": "\"Missing field email\""}
'"Missing field email"'

$ python3 -c 'from api.problems import problem; print(problem(400, detail={"field":"email"})[2])'
{"type": "about:blank", "title": "Bad Request", "status": "400", "detail": "{\"field\": \"email\"}"}

$ python3 -c 'from api.problems import validation_problem; print(validation_problem([])[2])'
{"type": "/problems/validation-error", "title": "Your request is not valid.", "status": "422", "detail": "\"One or more fields failed validation.\"", "errors": []}
```

Grade: the JSON type is technically still a string, so the 3.1 MUST-ignore rule is not triggered. The content is not clean human-readable text, though: it has literal quote characters, or a JSON object encoded as a string. Getting the real message back means JSON-parsing `detail`, which runs against the 3.1.4 SHOULD NOT for consumers. Because it goes through `error_response` (api/errors.py:5), this affects every error in the API. No keyword is violated directly; I graded it a defect.

## 4. `about:blank` title is not the HTTP status phrase. RFC 4.2.1

RFC 4.2.1: "When "about:blank" is used, the title SHOULD be the same as the recommended HTTP status phrase for that code (e.g., "Not Found" for 404, and so on), although it MAY be localized".

Code: api/problems.py:19 `"title": title or TITLES.get(status, "Error"),`. TITLES (lines 7-13) covers only 400, 404, 409, 422, and 500. The code also takes a caller-supplied `title` even when `type` is `about:blank`.

Repro:
```
$ python3 -c 'from api.problems import problem
for c in (401,403,405,429,503): print(c, problem(c)[2])'
401 {"type": "about:blank", "title": "Error", "status": "401"}
403 {"type": "about:blank", "title": "Error", "status": "403"}
405 {"type": "about:blank", "title": "Error", "status": "405"}
429 {"type": "about:blank", "title": "Error", "status": "429"}
503 {"type": "about:blank", "title": "Error", "status": "503"}

$ python3 -c 'from api.problems import problem; print(problem(404, title="Widget missing")[2])'
{"type": "about:blank", "title": "Widget missing", "status": "404"}
```

Grade: SHOULD. The five mapped phrases match RFC 9110 ("Unprocessable Content" for 422 is correct).

## 5. `type` URI is relative or depends on the host. RFC 3.1.1 and 4

RFC 3.1.1: "it is RECOMMENDED that absolute URIs be used in "type" when possible and that when relative URIs are used, they include the full path (e.g., "/types/123")." Also: "Consumers MUST use the "type" URI (after resolution, if necessary) as the problem type's primary identifier."
RFC 4: "New problem type definitions MUST document: 1. a type URI".

Code, api/problems.py:18: `urljoin(request_url, PROBLEM_BASE + type_)`. `request_url` defaults to `""` in `problem` (line 16), `validation_problem` (line 31), and `error_response` (api/errors.py:4).

Repro:
```
$ python3 -c 'from api.problems import validation_problem; print(validation_problem([])[2])'
{"type": "/problems/validation-error", "title": "Your request is not valid.", "status": "422", "detail": "\"One or more fields failed validation.\"", "errors": []}

$ python3 -c 'from api.problems import validation_problem
for u in ("https://api.example.com/users","https://staging.example.net/v2/users","http://10.0.0.5:8080/users"): print(validation_problem([], request_url=u)[2])'
{"type": "https://api.example.com/problems/validation-error", "title": "Your request is not valid.", "status": "422", "detail": "\"One or more fields failed validation.\"", "errors": []}
{"type": "https://staging.example.net/problems/validation-error", "title": "Your request is not valid.", "status": "422", "detail": "\"One or more fields failed validation.\"", "errors": []}
{"type": "http://10.0.0.5:8080/problems/validation-error", "title": "Your request is not valid.", "status": "422", "detail": "\"One or more fields failed validation.\"", "errors": []}
```

Grade:
- The default output is a relative URI. It does include the full path, so it meets the fallback part of the RECOMMENDED but not the "absolute when possible" part. RECOMMENDED is equivalent to SHOULD.
- When a base is supplied, the type URI comes from whatever host or scheme served the request. Consumers MUST treat the type URI as the primary identifier, so the same problem type appears as a different type on each host, environment, or internal address. That is the confusion 3.1.1 warns about. It also means no single type URI can be documented as Section 4 requires.
- Whether this becomes an actual MUST-level breakage depends on what `request_url` callers pass in production. Nothing in the repo calls `problem`, `validation_problem`, or `error_response` with a URL (`git grep` finds no callers outside the tests), so **this cannot be determined from the repo**.
- Side effect: passing an internal URL as the base would leak internal hostnames into responses (see the 10.0.0.5 example). That is relevant to RFC 5 ("Risks include leaking information"), which carries no keyword.

## 6. `validation-error` problem type is undocumented. RFC 4

RFC 4: "New problem type definitions MUST document: 1. a type URI ... 2. a title ... 3. the HTTP status code". Also: "A problem type URI SHOULD resolve to HTML [HTML5] documentation that explains how to resolve the problem." And 3.1.1: dereferencing a locator type URI "SHOULD provide human-readable documentation".

Code: api/problems.py:34 defines `type_="validation-error"`, which becomes `/problems/validation-error`. The repo contains only `.gitignore`, `api/__init__.py`, `api/errors.py`, `api/problems.py`, `repo.bundle`, and `tests/test_problems.py`, plus `.claude/` tooling. There is no docs directory, no route serving `/problems/*`, and no docstring documenting the type's title or status, or the `errors` extension's schema.

Repro:
```
$ git ls-files | grep -v '^.claude'
.gitignore
api/__init__.py
api/errors.py
api/problems.py
repo.bundle
tests/test_problems.py
$ ls docs
ls: cannot access 'docs': No such file or directory
```

Grade: MUST (documentation) and SHOULD (resolvable HTML). **Whether documentation exists outside this repo cannot be determined.** If it does not, this is a MUST nonconformance.

## 7. An extension can override the standard `type` member. RFC 3.1.1 and 3.2

Code, api/problems.py:26: `doc.update(extensions)` runs after the standard members are set. `status`, `title`, `detail`, and `instance` are named parameters, so Python rejects them as kwargs. `type` is not a parameter (the parameter is `type_`), so passing it overwrites the computed value with no warning.

Repro:
```
$ python3 -c 'from api.problems import problem; print(problem(404, **{"type":"https://other.example/x"})[2])'
{"type": "https://other.example/x", "title": "Not Found", "status": "404"}
```

Grade: no keyword. It lets a caller emit a `type` that skips `/problems/` resolution and contradicts the about:blank title logic. Extension members (3.2) are meant to add to the standard members, not replace them.

## 8. Extension member names are not checked. RFC 4

RFC 4: "their names SHOULD start with a letter ... and SHOULD comprise characters from ALPHA, DIGIT ..., and "_" ..., and they SHOULD be three characters or longer."

Code: api/problems.py:16 (`**extensions`) and :26 accept any key.

Repro:
```
$ python3 -c 'from api.problems import problem; print(problem(400, **{"_x":1,"ab":2,"a-b":3})[2])'
{"type": "about:blank", "title": "Bad Request", "status": "400", "_x": 1, "ab": 2, "a-b": 3}
```

Grade: SHOULD. The only extension used in-tree, `errors`, complies, so this is a latent issue only.

## 9. `instance` is passed through unchecked. RFC 3.1.5

RFC 3.1.5: "it is RECOMMENDED that absolute URIs be used in "instance" when possible, and that when relative URIs are used, they include the full path".

Code: api/problems.py:24-25.

Repro:
```
$ python3 -c 'from api.problems import problem; print(problem(404, instance="example-instance")[2])'
{"type": "about:blank", "title": "Not Found", "status": "404", "instance": "example-instance"}
```

Grade: RECOMMENDED. This is latent: no in-repo caller sets `instance`, and the type (a string) is not enforced either.

## 10. `type_` is not tied to its status code, and it is path-resolved. RFC 4 and 3.1.1

RFC 4 requires a type definition to document "the HTTP status code for it to be used with". `problem()` lets any `type_` be used with any status. `type_` is also concatenated and passed to `urljoin`, so `..` escapes `/problems/`.

Repro:
```
$ python3 -c 'from api.problems import problem; print(problem(404, type_="validation-error")[2])'
{"type": "/problems/validation-error", "title": "Not Found", "status": "404"}

$ python3 -c 'from api.problems import problem; print(problem(404, type_="../../admin", request_url="https://api.example.com/users")[2])'
{"type": "https://api.example.com/admin", "title": "Not Found", "status": "404"}
```

The first output also shows the `title` falling back to the status phrase ("Not Found") for a non-about:blank type, instead of the type's own title. 3.1.3 says the title "SHOULD NOT change from occurrence to occurrence of the problem", so the same type gets different titles depending on the status passed in. That is a SHOULD.

Grade: SHOULD (3.1.3 title stability). The RFC 4 status binding is a MUST on the *definition*, so I cannot call it a violation without that definition (see #6). The traversal is a robustness issue with no keyword.

---

## Checked and conformant (within this layer)

- When `type_` is omitted, `type` is `about:blank` (3.1.1, 4.2.1). Covered by `test_default_type_is_about_blank`.
- The body's `status` value equals the returned HTTP status (3.1.2 MUST), apart from the JSON-type problem in #1.
- `errors` is a reasonable extension member name (3.2, 4). Its item shape (`field`/`msg`) differs from the RFC's illustrative `detail`/`pointer` example, but that example is not normative.
- `title` for `validation_problem` is constant per type (3.1.3), and the five mapped status phrases match RFC 9110.
- `python3 -m pytest -q tests` gives `2 passed in 0.01s`. The tests do not check Content-Type, the JSON type of `status`, the `detail` content, absolute `type`, or titles for unmapped statuses, which is why #1 through #5 pass CI.

## Not checked or cannot be determined

- **HTTP wire behavior.** The repo has no server or framework. `problem()` returns a `(status, headers, body)` tuple, and I could not see how it becomes an HTTP response: whether headers are preserved, whether a charset is added, or whether a framework rewrites Content-Type. Findings #1 and #2 are about what this code emits, not what is verified on the wire.
- **Callers and `request_url` in production.** There are no in-repo callers, so the real-world impact of #5 (host-dependent type URIs, internal host leakage) cannot be determined.
- **External problem-type documentation** (#6): cannot be determined from the repo.
- **Content negotiation** (Section 1, Section 3 example, 12.5.1 of RFC 9110): no Accept handling exists to check. `error_response` previously returned `{"error": message}` and now returns problem details unconditionally. That breaks clients reading `error`, which matters for the RFC 4 note about adding support "using HTTP content negotiation", but it is not an RFC requirement.
- **Security considerations (Section 5):** `error_response` passes `message` straight into `detail`. Whether callers put stack traces or internal data there cannot be determined without callers.
- **Not implemented, so not reviewed:** Appendix B XML format (`application/problem+xml`), Appendix C HTML embedding, localization via Accept-Language (4.2.1 MAY), Retry-After (4), IANA registration (4.2), and JSON Pointer usage in `errors`.
- **Out of scope:** the ~1,950 lines added under `.claude/` (tpm skill, guard and shim scripts, hook settings), the `.gitignore` entry, and the committed `repo.bundle`, all from commit ee00a75 "eval setup". They are not related to RFC 9457 and were not reviewed or executed. `.claude/settings.json` registers PreToolUse, Stop, and UserPromptExpansion hooks that run `.claude/skills/tpm/scripts/shim_claude.py`, which reviewers of this branch should be aware of.
