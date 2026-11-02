You are a scribe. Write two files, nothing else, and do not read any other file.

1. /tmp/cr-run.gJziX0MU/repo/outputs/subagent-prompt-02.md containing exactly the text between the BEGIN/END markers below (not the markers themselves):
BEGIN-02
Review main..feature/problem-details in /tmp/cr-run.gJziX0MU/repo for conformance with RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457), against the Ask/Scope/Decisions of workstreams/rfc9457-review.md@8800a8c on local branch `orchestration` (read it with `git -C /tmp/cr-run.gJziX0MU/repo show 8800a8c:workstreams/rfc9457-review.md | sed '/^## Notes/,$d'`; read nothing past that). No code changes; exercise the code and give each finding RFC section, file:line, and a repro command with its real output; list what you didn't check; "can't determine" is a valid result. Write the full review to /tmp/cr-run.gJziX0MU/repo/outputs/rfc9457-review.md and reply with it.
END-02

2. /tmp/cr-run.gJziX0MU/repo/outputs/subagent-prompt-03.md containing this entire message verbatim, from "You are a scribe." through the final line.

Reply with the two paths and `wc -c` of each. If you can't, say why.
