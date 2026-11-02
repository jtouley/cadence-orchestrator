# Security policy

## Reporting a vulnerability

Please report security problems privately, not in a public issue. Use GitHub's private vulnerability reporting:
**Security → Report a vulnerability** on
[github.com/jtouley/cadence-orchestrator](https://github.com/jtouley/cadence-orchestrator/security/advisories/new).
Include what you found, how to reproduce it, and which version you used. You'll get a reply in the advisory.

## Supported versions

Only the latest 0.1.x release on npm (`cadence-orchestrator`) gets security fixes. Upgrade with
`npx cadence-orchestrator@latest --target <platform>` and commit the result.

## Scope

The tpm guard is **not a sandbox**. It keeps a cooperative orchestrating agent from drifting into doing the work
itself; its shell check and off-switch protection are text filters a determined model can get around, it fails
open on errors, and on Codex, Cursor and Gemini it only warns. A way to get past the guard is a bug worth
reporting, but not a security boundary being broken. Reports in scope include, for example: the installer
writing outside the target repo, a hook running code it shouldn't (such as an import planted in a shared
directory), or leaked secrets or personal data in the package or the repo.
