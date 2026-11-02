Before anything else, save this entire prompt, verbatim and unchanged, to /tmp/cr-run.3gPzEfIN/repo/outputs/subagent-prompt-01.md (create outputs/ if needed); touch nothing else in the repo.

Review the change main..184d27c in /tmp/cr-run.3gPzEfIN/repo (the branch also exists in repo.bundle there) for conformance against RFC 9457, https://www.rfc-editor.org/rfc/rfc9457 — read the RFC itself and exercise the code (run the tests and/or call the error helpers to inspect actual serialized output). Ignore files under .claude/ and .cadence/. Read-only: no fixes, no commits.

Report each nonconformance with: the RFC section and its MUST/SHOULD level, file:line, a repro command and its raw output, and severity. Also list things you checked that do conform, and anything you couldn't check and why. If something can't be determined, say so rather than guessing.
