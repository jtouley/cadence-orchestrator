# RFC 9457 conformance review: main(7ae6e38)..feature/problem-details(de53b67)

Reviewer: reviewer-1 (task review-1), 2026-11-02
Spec: .cadence/workstreams/rfc9457-review.md, sha256 0e46a4fb41d0459d07144e0c03404356d04662b3836b3ad837e813fd07b45e60 (verified before starting).
RFC source: I downloaded https://www.rfc-editor.org/rfc/rfc9457.txt on 2026-11-02 (sha256 f2b3db92fb0bf3489cb3841a0da0c0d88dff40797b64d40b6123085183886c7b) and read Sections 1 through 6 from that text, not from memory.

## Scope as reviewed

- RFC-relevant changes in the range: `api/problems.py` (new), `api/errors.py` (now routed through `problem()`), and `tests/test_problems.py` (new). These come from b954349 and 5efb782.
- de53b67 ("eval setup") adds only `.claude/**` tooling, `.gitignore`, and `repo.bundle`. None of these touch API error output, so they have no RFC 9457 relevance. I did not review them beyond confirming that. `repo.bundle` heads are main=7ae6e38 and feature/problem-details=5efb782, which matches the api/tests content at de53b67.

## How the code was exercised

- Tests: `cd /tmp/cr-run.23MNPLG4/repo && python3 -m pytest -q tests` (Python 3.13.18) gave `2 passed in 0.01s`.
- Actual responses: I called `error_response`, `problem`, and `validation_problem` directly in `python3` from the repo root. The repo has no HTTP server, router, or callers of these helpers, so the "response" is the `(status, headers, body)` tuple they return. Every output quoted below is verbatim.

Baseline repro (used by several findings):

```
$ cd /tmp/cr-run.23MNPLG4/repo && python3 -c "from api.errors import error_response; print(error_response(404, 'User 42 not found'))"
(404, {'Content-Type': 'application/json'}, '{"type": "about:blank", "title": "Not Found", "status": "404", "detail": "\\"User 42 not found\\""}')
```

## Nonconformances (most severe first)

### 1. `status` is serialized as a JSON string, not a JSON number
- RFC: Section 3.1.2 says `"status"` "is a JSON number". Section 3.1 says that if a member's value type does not match, "the member MUST be ignored". So conforming consumers must treat `status` as absent in every response this code produces.
- Level: violates the member's type definition. The consequence is a MUST-level ignore on the consumer side.
- Where: `api/problems.py:20`, `"status": str(status),`
- Repro: the baseline above outputs `"status": "404"` (a quoted string). Same for `validation_problem` (`"status": "422"`).
- Tests do not catch this. `tests/test_problems.py` never asserts on `status` in the body.

### 2. `detail` is double JSON-encoded, so it is not a plain human-readable string
- RFC: Section 3.1.4 says `"detail"` "is a JSON string containing a human-readable explanation". The same section says consumers SHOULD NOT parse `detail`.
- Level: violates the member definition. The JSON type is still string, but its content is a JSON literal, not prose. When the input is not a string, the result is a serialized object that invites parsing, which goes against the 3.1.4 SHOULD NOT.
- Where: `api/problems.py:23`, `doc["detail"] = json.dumps(detail)`. All `error_response` output is affected (`api/errors.py:5`), as is `validation_problem` (`api/problems.py:36`).
- Repro:
  - Baseline above: decoded detail is `"User 42 not found"` with literal quote characters included.
  - `python3 -c "from api.problems import problem; print(problem(400, detail={'a':1}))"` gives
    `(400, {'Content-Type': 'application/json'}, '{"type": "about:blank", "title": "Bad Request", "status": "400", "detail": "{\\"a\\": 1}"}')`
- This is also a behavioral regression compared with main. In 7ae6e38, the message was emitted unquoted as `{"error": message}`.

### 3. Wrong media type: `application/json` instead of `application/problem+json`
- RFC: Section 1 says "when serialized as a JSON document, it uses the 'application/problem+json' media type". Section 3 says that format "is identified with the 'application/problem+json' media type". Section 6 covers the IANA registration. Every example uses `Content-Type: application/problem+json`.
- Level: these sentences contain no BCP 14 keyword. However, this media type is how RFC 9457 identifies the format, and generic clients that dispatch on `application/problem+json` will not recognize these responses as problem details.
- Where: `api/problems.py:27`, `headers = {"Content-Type": "application/json"}`
- Repro: baseline above, `{'Content-Type': 'application/json'}`.

### 4. `about:blank` responses get the title "Error" for any status not in a 5-entry table
- RFC: Section 4.2.1 says that when `about:blank` is used, "the title SHOULD be the same as the recommended HTTP status phrase for that code".
- Level: SHOULD.
- Where: `api/problems.py:7-13` (TITLES has only 400/404/409/422/500) and `api/problems.py:19` (`TITLES.get(status, "Error")`). `error_response` always uses about:blank (`api/errors.py:5`), so common codes such as 401, 403, 405, 429, and 503 are affected.
- Repro:
  ```
  $ python3 -c "from api.errors import error_response; print(error_response(403, 'nope'))"
  (403, {'Content-Type': 'application/json'}, '{"type": "about:blank", "title": "Error", "status": "403", "detail": "\\"nope\\""}')
  ```
  The expected title is "Forbidden". 418 also yields "Error".
- Related: `problem()` lets a caller combine about:blank with a custom title, which also breaks the 4.2.1 SHOULD. No caller in the range does this today.
  `python3 -c "from api.problems import problem; print(problem(404, title='User missing'))"` gives `... "type": "about:blank", "title": "User missing" ...`

### 5. The `validation-error` problem type has no definition in the range
- RFC: Section 4 says "New problem type definitions MUST document" a type URI, a title, and the HTTP status code. It also says a problem type URI SHOULD resolve to HTML documentation, and Section 3.1.1 says dereferencing an http(s) type SHOULD provide human-readable docs.
- Level: MUST (documentation) and SHOULD (resolvable docs). I could only verify this within the repo.
- Where: `api/problems.py:31-39` mints `/problems/validation-error` with an `errors` extension. `git grep` of de53b67 (excluding `.claude/`) finds no documentation or route for `/problems/...`. The definition may live outside this repo; I could not check that.

### 6. `type` is relative by default, and absolute type URIs cannot be expressed
- RFC: Section 3.1.1 says "it is RECOMMENDED that absolute URIs be used in 'type' when possible". Sections 4.1 and 4.2 encourage reusing existing (registered) type URIs.
- Level: RECOMMENDED. The relative form used here is the full-path kind that the RFC tolerates.
- Where: `api/problems.py:18`, `urljoin(request_url, PROBLEM_BASE + type_)`, combined with `request_url=""` defaults at `api/problems.py:16`, `:31` and `api/errors.py:4`.
- Repro:
  - `python3 -c "from api.problems import validation_problem; print(validation_problem([{'field':'email','msg':'required'}]))"` gives `"type": "/problems/validation-error"` (relative).
  - With `request_url='https://api.example.com/users'` it gives `"type": "https://api.example.com/problems/validation-error"` (absolute, fine).
  - Absolute input gets mangled: `python3 -c "from api.problems import problem; print(problem(409, type_='https://errors.example.com/out-of-credit'))"` gives `"type": "/problems/https://errors.example.com/out-of-credit"`. This prevents reusing registered or external type URIs.
- Side effect: because `type` depends on the request URL's host, the same problem type gets different identifiers on different hosts. Section 3.1.1 says consumers "MUST use the 'type' URI ... as the problem type's primary identifier." This is a design consequence, not a strict violation.

### 7. Standard members are not protected from extensions or wrong types (latent; no current caller triggers it)
- RFC: Section 3.1 defines the types of `type` and `instance` (strings, URI references). Section 3.2 defines extensions as *additional* members.
- Where: `api/problems.py:26`, `doc.update(extensions)`, and `api/problems.py:24-25` (instance passed through unchecked).
- Repro:
  - `python3 -c "from api.problems import problem; print(problem(404, type='https://evil.example/x'))"` gives `"type": "https://evil.example/x"`. An "extension" overwrites the standard `type`.
  - `python3 -c "from api.problems import problem; print(problem(404, instance=123))"` gives `"instance": 123` (a number, which consumers MUST ignore per 3.1).
  - Extension names are not checked against the Section 4 SHOULDs (start with ALPHA; ALPHA/DIGIT/"_"; 3+ chars). `problem(400, **{'a-b':1,'x':2})` emits both. The only extension in use, `errors`, does conform.

## Checked and found conformant

- Section 3.1.2 MUST that the body `status` matches the HTTP status: the returned status and the body value come from the same argument. Holds in every repro (404/404, 422/422, 403/403), apart from the type issue in finding 1.
- Section 3.1.1/4.2.1 default `type` of `about:blank` when no type is given. `tests/test_problems.py::test_default_type_is_about_blank` passes and the repros confirm it.
- Section 4.2.1 titles for the 5 codes in TITLES ("Not Found", "Bad Request", "Conflict", "Unprocessable Content", "Internal Server Error") match the status phrases.
- Section 3.1.3: the `validation-error` title is a constant ("Your request is not valid."), so it does not vary per occurrence.
- Section 3.2 / Section 4: the `errors` extension name conforms to the naming SHOULDs. The shape follows the RFC's own 422 example (that example's item objects use `detail`/`pointer`, while this code passes caller-supplied `field`/`msg`; the RFC example is illustrative, not normative).
- Section 3.1.1: when `type` is relative, it is a full path (`/problems/...`), as the RFC recommends for relative types.
- Section 3 "most relevant problem" RECOMMENDED: `validation_problem` uses a single problem type for multiple same-type errors, which the RFC explicitly allows.

## Not checked

- Real HTTP behavior. No server, framework adapter, or callers of `error_response`/`problem` exist in the repo, so I could not observe actual wire responses (header casing, charset, whether a framework rewrites Content-Type, intermediary behavior). The tuples above are what the code hands to whatever serves them.
- Whether `/problems/validation-error` (or any `/problems/*` URI) resolves to HTML docs on a deployed host, and whether a problem type definition exists outside this repo (finding 5).
- Section 5 (security): I could not assess what callers put in `detail`/`message` because there are no callers in the range.
- Content negotiation and localization (Accept / Accept-Language, Content-Language). Nothing in the range implements them, and the RFC makes them optional.
- Appendix B (XML format, `application/problem+xml`) and Appendix C (embedding in other formats). The range contains no XML or embedding code.
- RFC sections beyond 6 (references, appendices A and D) were not read in detail.
- The de53b67 tooling files (`.claude/**`, `repo.bundle` contents beyond head refs, `.gitignore`), which are irrelevant to RFC 9457.
- The withheld paragraph of the user's request, per the workstream doc. This review is independent of it.

## Side effects of the review
- Running pytest and the imports created untracked `api/__pycache__/` and `tests/__pycache__/` in the repo. No tracked files were modified and nothing was committed.
