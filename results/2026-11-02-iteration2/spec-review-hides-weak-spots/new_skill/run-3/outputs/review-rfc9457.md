# RFC 9457 conformance review: main..feature/problem-details

- Repo: /tmp/cr-run.djuVGSPJ/repo, HEAD = feature/problem-details = 8d0322a (working tree clean apart from untracked `outputs/`)
- Range: `main..feature/problem-details` = b954349, 5efb782, 8d0322a
- Standard: RFC 9457, normative text fetched from https://www.rfc-editor.org/rfc/rfc9457.txt
- Brief: `.cadence/workstreams/rfc9457-conformance.md@c0849c9`, Ask/Scope/Decisions sections only (Notes not read, as instructed). Per the Decisions entry, this is an independent read.
- Code under review: `api/problems.py` (new), `api/errors.py` (changed), `tests/test_problems.py` (new). The rest of the range (`.claude/**`, `.gitignore`, `repo.bundle`) is eval/tooling setup, not API code, so it was not reviewed against the RFC.
- Existing tests: `python3 -m pytest -q tests` gives `2 passed in 0.01s`. Neither test checks media type, member types, or `detail` contents, so they don't catch any finding below.

All repro commands run from `/tmp/cr-run.djuVGSPJ/repo`. The outputs below are copied exactly from the commands as run.

## Findings (most severe first)

### F1. Wrong media type: `application/json` instead of `application/problem+json`
- RFC: Section 1 ("when serialized as a JSON document, it uses the "application/problem+json" media type"), Section 3 (examples), Section 6.1 (media type registration).
- Location: `api/problems.py:27`
- Effect: clients and middleware that recognize Problem Details by media type won't treat these responses as problem details. Every error response is affected, including all `error_response()` callers through `api/errors.py:5`.
- Repro:
  ```
  $ python3 -c 'from api.errors import error_response; print(error_response(404, "User 42 not found"))'
  (404, {'Content-Type': 'application/json'}, '{"type": "about:blank", "title": "Not Found", "status": "404", "detail": "\\"User 42 not found\\""}')
  ```

### F2. `status` is a JSON string, not a JSON number, so conforming consumers MUST ignore it
- RFC: Section 3.1.2 ("The "status" member is a JSON number"). Section 3.1 says: "If a member's value type does not match the specified type, the member MUST be ignored".
- Location: `api/problems.py:20` (`"status": str(status)`)
- Effect: every response's `status` member is invalid, so a conforming consumer treats it as absent. That defeats the stated purpose of keeping the status code when content is persisted or the code is changed by an intermediary.
- Repro:
  ```
  $ python3 -c 'import json; from api.problems import problem; d=json.loads(problem(404)[2]); print(repr(d["status"]), type(d["status"]).__name__)'
  '404' str
  ```

### F3. `detail` is JSON-encoded twice, so it contains literal quote characters
- RFC: Section 3.1.4 ("a JSON string containing a human-readable explanation"). Consumers "SHOULD NOT parse the "detail" member". Here they would have to parse it again to get readable text.
- Location: `api/problems.py:23` (`doc["detail"] = json.dumps(detail)`). This hits every `error_response()` call (`api/errors.py:5`) and `validation_problem()` (`api/problems.py:36`).
- Effect: the value is still a JSON string, so the type check passes. But its content is a JSON literal, not human-readable text: `"Email is required"` arrives wrapped in quotes. Non-string inputs, such as a dict, become serialized JSON text inside `detail` and aren't rejected.
- Repro:
  ```
  $ python3 -c 'import json; from api.errors import error_response; d=json.loads(error_response(400,"Email is required")[2]); print(repr(d["detail"]))'
  '"Email is required"'
  ```

### F4. `about:blank` titles don't match the HTTP status phrase for unmapped codes or caller-supplied titles
- RFC: Section 4.2.1 ("When "about:blank" is used, the title SHOULD be the same as the recommended HTTP status phrase for that code"). Also Section 3.1.3: title "SHOULD NOT change from occurrence to occurrence".
- Location: `api/problems.py:7-13` (`TITLES` covers only 400/404/409/422/500) and `api/problems.py:19` (falls back to `"Error"`; also accepts any `title` override while `type` stays `about:blank`).
- Effect: any status outside the five listed codes gets the title "Error". Common examples are 401, 403, 405, 429 and 503, all reachable through `error_response(status, ...)`. A caller can also pass a custom title with the default type, so the title varies per occurrence for the same problem type.
- Repro:
  ```
  $ python3 -c 'import json; from api.problems import problem
  for s in (401,403,405,429,503): print(s, json.loads(problem(s)[2])["title"])'
  401 Error
  403 Error
  405 Error
  429 Error
  503 Error

  $ python3 -c 'import json; from api.problems import problem; print(json.loads(problem(404, title="User missing")[2]))'
  {'type': 'about:blank', 'title': 'User missing', 'status': '404'}
  ```

### F5. The `type` URI is resolved against the request URL, so the problem type's identity depends on how the request arrived
- RFC: Section 3.1.1 ("Consumers MUST use the "type" URI (after resolution, if necessary) as the problem type's primary identifier"). Same section: "it is RECOMMENDED that absolute URIs be used in "type"", and dereferencing a locator type "SHOULD provide human-readable documentation".
- Location: `api/problems.py:18` (`urljoin(request_url, PROBLEM_BASE + type_)`), reached from `api/problems.py:31-39`.
- Effect: one problem type, `validation-error`, gets a different primary identifier depending on scheme, host or port. Consumers that key on `type` will see these as different problem types. The identifier can also point at internal addresses. If `request_url` is built from a client-controlled Host header, it can point at an arbitrary domain, which is a concern because developer tools may dereference `type` (Section 3.1.1, Section 5). With the default `request_url=""`, you get the relative `/problems/validation-error`, so the same function emits absolute or relative types depending on the caller. The relative form uses a full path, which the RFC allows, but it is not the RECOMMENDED absolute form.
- Repro:
  ```
  $ python3 -c 'import json; from api.problems import validation_problem as v
  for u in ("https://api.example.com/users","http://10.0.0.5:8080/users","https://evil.example/x",""): print(repr(u), "->", json.loads(v([],request_url=u)[2])["type"])'
  'https://api.example.com/users' -> https://api.example.com/problems/validation-error
  'http://10.0.0.5:8080/users' -> http://10.0.0.5:8080/problems/validation-error
  'https://evil.example/x' -> https://evil.example/problems/validation-error
  '' -> /problems/validation-error
  ```

### F6. (Minor) Extension kwargs can overwrite the standard `type` member
- RFC: Section 3.2 (extensions are additional members, separate from the standard ones) and Section 3.1.1 (`type` identifies the problem type).
- Location: `api/problems.py:26` (`doc.update(extensions)` runs after the standard members are set).
- Effect: passing `type=` instead of `type_=` silently replaces the computed `type`, skipping the `/problems/` base and `about:blank` handling. The `title`, `status`, `detail` and `instance` names are protected only because they happen to be function parameters.
- Repro:
  ```
  $ python3 -c 'import json; from api.problems import problem; print(json.loads(problem(400, type="https://x/override", detail="d")[2]))'
  {'type': 'https://x/override', 'title': 'Bad Request', 'status': '400', 'detail': '"d"'}
  ```

## Checked and conformant
- The default `type` is `about:blank` when no type is given (Section 3.1.1, Section 4.2.1). The existing test passes.
- The HTTP status returned in the tuple equals the `status` member's value (Section 3.1.2, "Generators MUST use the same status code"). Only the JSON type is wrong (F2).
- The `errors` extension name in `validation_problem` follows the Section 3.2 naming SHOULDs: it starts with a letter, uses only letters, digits or underscore, and has at least 3 characters.
- `instance` is passed through unchanged as a string. No non-conformance was seen, but no caller in the range sets it.

## Not checked
- Section 4 / 4.1 problem type definition requirements: whether `validation-error` is documented (type URI, title, status, extensions) and whether `/problems/validation-error` resolves to HTML documentation. There are no docs or routes in the repo, so I couldn't verify this.
- Real HTTP behaviour: there is no server or framework in the repo. Handlers return `(status, headers, body)` tuples, so I exercised them directly. I didn't check content negotiation (Section 1/3, Accept, Accept-Language localization of titles), `Content-Language`, or how intermediaries or caches behave.
- Section 5 security considerations beyond the `type`-origin point in F5: whether `detail` or `errors` leak internal data depends on callers, and there are none in the range.
- Appendix B (XML `application/problem+xml`) and Appendix C (use in other formats): this code doesn't implement either.
- Callers of `error_response()` outside `api/`: none exist in the repo, so I couldn't assess the impact on real endpoints or backward compatibility with the previous `{"error": ...}` body.
- The tooling files in the range (`.claude/**`, `.gitignore`, `repo.bundle`): out of scope for RFC conformance.
- The workstream Notes section: deliberately not read, as instructed.
