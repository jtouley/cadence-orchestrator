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
2. After it merges, the owner tags the merge commit on `main` with an annotated tag (its date is the release time
   `dora` uses) and pushes it:

   ```sh
   git switch main && git pull
   git tag -a v0.1.4 -m "v0.1.4"
   git push origin v0.1.4
   ```

3. `.github/workflows/release.yml` runs two jobs:
   - `verify`, with no publishing rights: the tag matches `package.json` and is on `main`, the version isn't on
     npm yet (so a re-tag fails early), then the tests and the package check.
   - `publish`, in the `npm-release` environment: `npm publish --provenance --access public`, with prereleases
     (`1.2.3-rc.1`) going to the `next` dist-tag.

Pushing the tag is the approval only if nobody else can push one or publish. Set up once:

- **Environment** `npm-release` (Settings → Environments): add the secret `NPM_TOKEN` there, not as a repository
  secret, add the owner as a required reviewer, and limit its deployment tags to `v*`.
- **Tag ruleset** (Settings → Rules → Rulesets, target tags `v*`): restrict creation, update and deletion to the
  owner.

## Repository settings (maintainers)

To enforce pull requests on GitHub as well, add a ruleset under **Settings → Rules → Rulesets** that targets the
default branch, with:

- **Require a pull request before merging**
- **Require status checks to pass**, listing the CI jobs (`pre-commit`, `leaks`, `pytest`, `installer`)
- **Block force pushes**
- **Restrict deletions**

The `orchestration` branch used by the skill needs its own pre-commit setup; see
[`skills/tpm/references/workstream.md`](skills/tpm/references/workstream.md).
