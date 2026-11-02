# RFC 9457 conformance review: main..feature/problem-details

- Repo: /tmp/cr-run.gJziX0MU/repo, range `main..feature/problem-details` (b954349, 5efb782, 08e0ff0)
- Brief: workstreams/rfc9457-review.md@8800a8c (Ask/Scope/Decisions only; nothing from `## Notes` onward was read)
- Standard: RFC 9457. The text was downloaded from https://www.rfc-editor.org/rfc/rfc9457.txt and the quotes below come from it.
- Method: read the diff, then called `problem()`, `validation_problem()` and `error_response()` directly. All repro commands run from the repo root with python3.13. No code was changed.
- Independence: I worked from the RFC text and the code only. I did not see the user's hunches.

Files in the range that matter for RFC conformance: `api/problems.py` (new), `api/errors.py` (modified) and `tests/test_problems.py` (new). Commit 08e0ff0 "eval setup" adds `.claude/**`, `.gitignore` and `repo.bundle`. None of those produce HTTP error responses, so they have nothing to check against RFC 9457 (see "Not checked").

Baseline: the branch's own tests pass (`python3 -m pytest -q -p no:cacheprovider tests` -> `2 passed in 0.01s`). They only check `type == "about:blank"` and the `errors` extension, so none of the findings below are covered by a test.

---

## Findings (non-conformances)

### F1. `status` is a JSON string, not a JSON number (High)
- RFC: §3.1.2: "The "status" member is a JSON number indicating the HTTP status code". §3.1: "If a member's value type does not match the specified type, the member MUST be ignored". A conforming consumer therefore discards `status` on every response.
- Code: api/problems.py:20 `"status": str(status),`
- Repro:
  ```
  $ python3 -c 'import json; from api.problems import problem; d=json.loads(problem(404)[2]); print(repr(d["status"]), type(d["status"]).__name__)'
  '404' str
  ```
- Applies to every response, including those from `error_response()` and `validation_problem()`.

### F2. Responses are labelled `application/json`, not `application/problem+json` (High)
- RFC: §3: "When serialized in a JSON document, that format is identified with the "application/problem+json" media type." The §3 examples and the §6 registration say the same. The RFC does not phrase this as a MUST. But without the media type, generic clients can't tell a problem-details body from any other JSON, which is the whole point of the format.
- Code: api/problems.py:27 `headers = {"Content-Type": "application/json"}`
- Repro:
  ```
  $ python3 -c 'from api.problems import problem; print(problem(404)[1])'
  {'Content-Type': 'application/json'}
  ```

### F3. `detail` is double-encoded: it contains serialized JSON, not human-readable text (Medium-High)
- RFC: §3.1.4: "The "detail" member is a JSON string containing a human-readable explanation specific to this occurrence of the problem." and "Consumers SHOULD NOT parse the "detail" member for information; extensions are more suitable".
- Code: api/problems.py:23 `doc["detail"] = json.dumps(detail)`. This is reached from api/errors.py:5 and api/problems.py:36.
- Repro:
  ```
  $ python3 -c 'from api.errors import error_response; print(error_response(404, "User 42 not found")[2])'
  {"type": "about:blank", "title": "Not Found", "status": "404", "detail": "\"User 42 not found\""}

  $ python3 -c 'from api.errors import error_response; print(error_response(400, {"field": "email"})[2])'
  {"type": "about:blank", "title": "Bad Request", "status": "400", "detail": "{\"field\": \"email\"}"}
  ```
- After decoding, `detail` is still a JSON string, so its type conforms. Its content does not: string details arrive wrapped in literal quote characters. Structured messages arrive as a JSON document inside `detail`, which consumers would have to parse. §3.1.4 says that kind of data belongs in an extension member.

### F4. With `about:blank`, `title` is not the HTTP status phrase for any status missing from `TITLES`, and callers can override it (Medium)
- RFC: §4.2.1: "When "about:blank" is used, the title SHOULD be the same as the recommended HTTP status phrase for that code (e.g., "Not Found" for 404 ...)". Localization is the only exception.
- Code: api/problems.py:19 `"title": title or TITLES.get(status, "Error"),` and the table at api/problems.py:7-13. The table has only 400/404/409/422/500, and those five phrases match RFC 9110. Any other status (401, 403, 405, 406, 415, 429, 502, 503, ...) falls back to `"Error"`. A caller-supplied `title` is also used even when `type` is `about:blank`. `error_response()` (api/errors.py:5) always produces `about:blank`, so every status it emits outside the table gets `"title": "Error"`.
- Repro:
  ```
  $ python3 -c 'from api.problems import problem; print(problem(403)[2]); print(problem(429)[2]); print(problem(404, title="Nope")[2])'
  {"type": "about:blank", "title": "Error", "status": "403"}
  {"type": "about:blank", "title": "Error", "status": "429"}
  {"type": "about:blank", "title": "Nope", "status": "404"}
  ```

### F5. `type` is built without encoding and can be an invalid URI reference (Low-Medium)
- RFC: §3.1.1: "The "type" member is a JSON string containing a URI reference [URI]". RFC 3986 does not allow a literal space in a URI.
- Code: api/problems.py:18 `urljoin(request_url, PROBLEM_BASE + type_)`. `type_` is concatenated as-is, with no percent-encoding or validation.
- Repro:
  ```
  $ python3 -c 'from api.problems import problem; print(problem(400, type_="out of credit", request_url="https://api.example.com/a")[2])'
  {"type": "https://api.example.com/problems/out of credit", "title": "Bad Request", "status": "400"}
  ```
- The only in-tree caller, `validation_problem`, passes the safe slug `"validation-error"`. This is a trap in the helper, not something current output does.

### F6. Extension kwargs can overwrite the standard `type` member with a non-string (Low)
- RFC: §3.1.1 says `type` is a JSON string. §3.1 says a mistyped member "MUST be ignored", so the consumer falls back to `about:blank` and the problem type is lost. §3.2 describes extensions as *additional* members.
- Code: api/problems.py:26 `doc.update(extensions)`. The parameter is named `type_`, so a caller who writes `type=` lands in `**extensions` and overwrites the computed `type`. `status`, `title`, `detail` and `instance` are named parameters, so they can't be clobbered this way.
- Repro:
  ```
  $ python3 -c 'from api.problems import problem; print(problem(400, type=123)[2])'
  {"type": 123, "title": "Bad Request", "status": "400"}
  ```

### F7. The `type` identifier depends on the request host, and is relative when `request_url` is omitted (Low, design risk against §3.1.1)
- RFC: §3.1.1: "Consumers MUST use the "type" URI (after resolution, if necessary) as the problem type's primary identifier." and "it is RECOMMENDED that absolute URIs be used in "type" when possible and that when relative URIs are used, they include the full path".
- Code: api/problems.py:5 `PROBLEM_BASE = "/problems/"` and api/problems.py:18. `request_url` defaults to `""` (api/problems.py:16, 31; api/errors.py:4).
- Repro:
  ```
  $ python3 -c 'from api.problems import validation_problem as v; e=[{"field":"email","msg":"required"}]; print(v(e, request_url="https://api.example.com/users")[2]); print(v(e, request_url="http://10.0.0.5:8080/users")[2]); print(v(e)[2])'
  {"type": "https://api.example.com/problems/validation-error", "title": "Your request is not valid.", "status": "422", "detail": "\"One or more fields failed validation.\"", "errors": [{"field": "email", "msg": "required"}]}
  {"type": "http://10.0.0.5:8080/problems/validation-error", "title": "Your request is not valid.", "status": "422", "detail": "\"One or more fields failed validation.\"", "errors": [{"field": "email", "msg": "required"}]}
  {"type": "/problems/validation-error", "title": "Your request is not valid.", "status": "422", "detail": "\"One or more fields failed validation.\"", "errors": [{"field": "email", "msg": "required"}]}
  ```
- The relative form `/problems/...` does include the full path, so on its own it meets the RFC's fallback recommendation. The risk is elsewhere: the identifier consumers must key on changes with whatever host or scheme the request came in on (public host, internal IP, http vs https). One problem type can therefore show up under several identities, and an internal host can leak into responses (see §5). Whether this happens in practice depends on what callers pass as `request_url`. **Can't determine**: there are no callers in the range.

---

## Checked and conforming
- §3.1.2 "Generators MUST use the same status code in the actual HTTP response": `problem()` returns the same `status` for the HTTP status and the body (api/problems.py:20, 28). Example: `problem(418)` returns `418` with body `"status": "418"`, matching apart from the string type in F1.
- §3.1.1 default: with no `type_`, the code emits `"about:blank"` (api/problems.py:18). The test covers this.
- §3.1.3: `validation_problem` uses a fixed title (`"Your request is not valid."`) that doesn't change between occurrences.
- §3.2: the `errors` extension is a legal extension member. The RFC's own example uses `errors` items shaped `{detail, pointer}`, while this test uses `{field, msg}`. That shape is a choice for the problem-type definition, not a conformance violation.
- §3.1.5 `instance`: passed through when given. Nothing in the range supplies it.
- TITLES entries 400/404/409/422/500 match the RFC 9110 reason phrases.

## Can't determine
- §4 / §3.1.1 SHOULD: whether `/problems/validation-error` dereferences to human-readable documentation, and whether that problem type is documented as §4 requires (type URI, title, status, extensions). Nothing in the range defines or serves those docs.
- §5 Security: `error_response(status, message)` puts any caller string into `detail`, so it could leak internal details. The range contains no callers of `error_response`, `problem` or `validation_problem` outside the tests, so I can't see what messages actually flow in.
- F7 in practice: depends on the `request_url` values real callers pass. None are in the range.
- Whether the HTTP layer that consumes the `(status, headers, body)` tuple adds or changes headers (for example, it could rewrite Content-Type and fix F2). No such layer is in the range.

## Not checked
- The `.claude/**` tooling, `.gitignore` and `repo.bundle` added by commit 08e0ff0. They are in the range but have no RFC 9457 surface, and I neither read nor ran them.
- Appendix B (XML format, `application/problem+xml`) and Appendix C (embedding in other formats). The code produces no XML.
- Content negotiation and `Accept` / `Accept-Language` handling (§3, §4.2.1 localization). No request-handling code is in the range.
- §3.2 XML-Name compatibility of extension names, beyond noting that `errors` is a valid name.
- Behaviour with non-int `status`, non-JSON-serializable extensions, or `None` titles beyond the cases shown.
- Any consumer-side behaviour, such as clients ignoring unknown extensions. There is no consumer code.
- Code outside `main..feature/problem-details`, per scope.
