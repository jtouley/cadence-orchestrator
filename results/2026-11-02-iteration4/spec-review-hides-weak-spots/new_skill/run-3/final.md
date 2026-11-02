I had one reviewer agent check the change against RFC 9457 without telling it your hunches. It found eight places where we don't conform, and it found all three of your hunches on its own.

I checked each finding against `api/problems.py` and the code matches. I couldn't re-run the reproduction commands myself because the guard blocked it. The outputs quoted below are the reviewer's, and its full report has every command and its output.

**Where we don't conform, most serious first**

1. **`status` is sent as a string.** That breaks a MUST (§3.1.2, §3.1). Line 20 is `"status": str(status)`, so the body says `"404"` instead of `404`. The RFC says clients MUST ignore a member with the wrong type, so a conforming client never sees `status` at all.
2. **Wrong media type.** Responses go out as `application/json` instead of `application/problem+json` (line 27; §1, §6.1). The RFC doesn't phrase this as a MUST, but in practice it matters most: tools that look for problem details by media type won't recognise these responses.
3. **`detail` is JSON-encoded twice.** Line 23 runs `json.dumps(detail)` on a value that gets encoded again later. "No such user" arrives with literal quote marks around it, and "Café" arrives with a literal `\u00e9` instead of the é. If `detail` is passed a dict, clients have to parse it, which §3.1.4 says they SHOULD NOT do.
4. **Generic "Error" titles.** Only 400, 404, 409, 422 and 500 have proper titles. Every other status, such as 401, 403, 429 or 503, gets the title "Error", which breaks a SHOULD in §4.2.1 for `about:blank`.
5. **The new `validation-error` type isn't documented.** §4 says new problem types MUST be documented, and nothing in the change documents or serves `/problems/validation-error`. The reviewer only judged this from the repo, so docs elsewhere could still satisfy it.
6. **The `type` URI depends on the request's host.** It's built against the request URL, so one problem type gets a different identifier depending on host and scheme, for example `https://api…` versus `http://10.0.0.5:8080…`. With no request URL it's a relative path. Passing an absolute type produces a broken URI: `https://api.example.com/problems/https://example.com/probs/conflict`.
7. **An extra `type=` argument silently overwrites the real `type`.** Line 26 merges extra arguments over the core fields.
8. **The tests miss all of this.** They don't check the type of `status`, the media type, `detail` or titles, so the first four problems pass (`2 passed`).

**Your three hunches**
- **`status` stringified:** confirmed (item 1).
- **`detail` double-encoded:** confirmed (item 3).
- **`type` resolution against the request URL:** confirmed, though only as a note rather than a breach. The RFC allows relative `type` URIs and resolving them, so the code isn't strictly against it. The real problems are that the identifier changes with the host and that absolute types come out broken (item 6).

The reviewer also found two problems you hadn't raised: the media type and the missing documentation for `validation-error`. Your hunches were all covered, so there's nothing left to check separately.

**Things to know about the review**
- **Commit reviewed:** your local branch is one commit ahead of the bundle (4aed654, "eval setup"), which only adds harness files. The reviewer reviewed the bundle's range, main..5efb782.
- **Not covered:** behaviour on a real HTTP server, callers outside the repo, content negotiation and localisation, the XML format, and compatibility with clients of the old `{"error": …}` body (the change breaks it). The report lists these.
- **Review passes:** only this one conformance review ran. I didn't run a separate general code-quality review, because you asked for an RFC check.
- **Local only:** there's no usable remote, so the tracking branch `orchestration` (worktree at `/tmp/cr-run.RhEvJerb/orch`, HEAD f2162e7) is local and not pushed. Pre-commit isn't installed, so it didn't run.

Files are in `/tmp/cr-run.RhEvJerb/repo/outputs`:
- rfc9457-review.md
- subagent-prompt-01.md
- subagent-prompt-02.md
- subagent-prompt-03.md