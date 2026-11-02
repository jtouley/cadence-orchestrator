# Contributing

Issues and pull requests are welcome at
[github.com/jtouley/cadence-orchestrator](https://github.com/jtouley/cadence-orchestrator/issues).

## Before you open a pull request

```sh
pip install pre-commit==4.7.0 pytest==9.1.1
pre-commit install
pre-commit run --all-files
pytest
```

`main` changes only through pull requests: the `no-commit-to-branch` hook refuses local commits to it. If you
change what the guard allows, update `skills/tpm/references/guard.md` in the same change.

## Reporting a regression

If something worked in an earlier release and broke in a later one, open an issue with the `regression` label and
say which version broke it. The release that fixes it lists the fix under `### Fixed (regression from X.Y.Z)` in
`CHANGELOG.md`; `npx cadence-orchestrator dora` counts these as failed deployments.

## Releasing (maintainers)

1. Bump `package.json` (and the skill's `metadata.version`, which a test keeps equal) and move the CHANGELOG's
   Unreleased entries under the new version, in a pull request.
2. After it merges, the owner tags the merge commit on `main` and pushes the tag. Pushing the tag is the approval:

   ```sh
   git switch main && git pull
   git tag -a v0.1.4 -m "v0.1.4"
   git push origin v0.1.4
   ```

3. `.github/workflows/release.yml` checks that the tag matches `package.json` and is on `main`, runs the tests and
   the package check, and runs `npm publish --provenance --access public`. It needs the repository secret
   `NPM_TOKEN` (an npm automation or granular token with publish rights).

## Repository settings (maintainers)

To enforce pull requests on GitHub as well, add a ruleset under **Settings → Rules → Rulesets** that targets the
default branch, with:

- **Require a pull request before merging**
- **Require status checks to pass**, listing the CI jobs (`pre-commit`, `leaks`, `pytest`, `installer`)
- **Block force pushes**
- **Restrict deletions**

The `orchestration` branch used by the skill needs its own pre-commit setup; see
[`skills/tpm/references/workstream.md`](skills/tpm/references/workstream.md).
