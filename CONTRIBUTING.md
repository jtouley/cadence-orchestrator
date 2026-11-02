# Contributing

Issues and pull requests are welcome at
[github.com/jtouley/cadence-orchestrator](https://github.com/jtouley/cadence-orchestrator/issues).

## Before you open a pull request

```sh
uv sync
uv run pre-commit install
uv run pre-commit run --all-files
uv run pytest
```

Development uses [uv](https://docs.astral.sh/uv/); the kit itself only needs `python3` and Node. The `dev`
dependency group in `pyproject.toml` lists pytest and pre-commit, and `uv.lock` pins them and their dependencies by
version and hash; CI runs `uv sync --locked`, which fails if the lock is out of date. pre-commit needs Python 3.11
or later (on 3.10 the group installs pytest only); `.python-version` makes `uv sync` default to 3.13. After changing the group, run `uv lock` and commit `uv.lock`.

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

## OpenSSF Scorecard and code scanning

`.github/workflows/scorecard.yml` runs [OpenSSF Scorecard](https://github.com/ossf/scorecard) on pushes to `main`,
weekly and when branch protection changes, and uploads its findings to the repository's code scanning (Security
tab). It isn't a required check: it doesn't run on pull requests. Results aren't published yet
(`publish_results: false`), so the job has only `security-events: write` and `contents: read`. Phase 2, deferred
until the repository is 90 days old (around 2027-01-29), sets `publish_results: true`, adds the badge, and adds only
`id-token: write` (to publish); `actions: read` is needed only for private repositories.

`.github/workflows/codeql.yml` runs CodeQL on the workflows (`actions`), Python and JavaScript for pull requests,
pushes to `main` and weekly.

Dependabot (`.github/dependabot.yml`) proposes weekly updates for the pinned actions, `uv.lock` and the pre-commit
hook revisions. CI's `leaks` job downloads the gitleaks release tarball named by `GITLEAKS_VERSION` in `ci.yml` and
checks it against `GITLEAKS_SHA256`; Dependabot doesn't update those. When it bumps the gitleaks hook `rev`, CI
fails (`.github/scripts/check_gitleaks_version.py`, also a test) until you set both to the new release (the sha256
of `gitleaks_<version>_linux_x64.tar.gz` is in that release's `gitleaks_<version>_checksums.txt`).
