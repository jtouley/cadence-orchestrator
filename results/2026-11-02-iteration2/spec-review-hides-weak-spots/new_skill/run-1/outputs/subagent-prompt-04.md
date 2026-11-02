Scribe task: write three plain-text record files in /tmp/cr-run.gJziX0MU/repo/outputs/. These are a log of prompts an orchestrator sent to helper agents. Write nothing else and read no other files.

File subagent-prompt-02.md: the exact text between the lines "=====BEGIN 02=====" and "=====END 02=====" (markers excluded).
File subagent-prompt-03.md: the exact text between "=====BEGIN 03=====" and "=====END 03=====" (markers excluded).
File subagent-prompt-04.md: this entire message verbatim, from "Scribe task:" through the last line.

=====BEGIN 02=====
Review main..feature/problem-details in /tmp/cr-run.gJziX0MU/repo for conformance with RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457), against the Ask/Scope/Decisions of workstreams/rfc9457-review.md@8800a8c on local branch `orchestration` (read it with `git -C /tmp/cr-run.gJziX0MU/repo show 8800a8c:workstreams/rfc9457-review.md | sed '/^## Notes/,$d'`; read nothing past that). No code changes; exercise the code and give each finding RFC section, file:line, and a repro command with its real output; list what you didn't check; "can't determine" is a valid result. Write the full review to /tmp/cr-run.gJziX0MU/repo/outputs/rfc9457-review.md and reply with it.
=====END 02=====

=====BEGIN 03=====
You are a scribe. Write two files, nothing else, and do not read any other file.

1. /tmp/cr-run.gJziX0MU/repo/outputs/subagent-prompt-02.md containing exactly the text between the BEGIN/END markers below (not the markers themselves):
BEGIN-02
Review main..feature/problem-details in /tmp/cr-run.gJziX0MU/repo for conformance with RFC 9457 (https://www.rfc-editor.org/rfc/rfc9457), against the Ask/Scope/Decisions of workstreams/rfc9457-review.md@8800a8c on local branch `orchestration` (read it with `git -C /tmp/cr-run.gJziX0MU/repo show 8800a8c:workstreams/rfc9457-review.md | sed '/^## Notes/,$d'`; read nothing past that). No code changes; exercise the code and give each finding RFC section, file:line, and a repro command with its real output; list what you didn't check; "can't determine" is a valid result. Write the full review to /tmp/cr-run.gJziX0MU/repo/outputs/rfc9457-review.md and reply with it.
END-02

2. /tmp/cr-run.gJziX0MU/repo/outputs/subagent-prompt-03.md containing this entire message verbatim, from "You are a scribe." through the final line.

Reply with the two paths and `wc -c` of each. If you can't, say why.
=====END 03=====

Reply with the three paths and `wc -c` output for each. If you can't do it, say exactly why.
