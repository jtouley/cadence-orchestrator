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

1. Bump `package.json` (and the skill's `metadata.version` and `.claude-plugin/plugin.json`'s `version`, which a
   test keeps equal) and move the CHANGELOG's Unreleased entries under the new version, in a pull request.
2. After it merges, the owner tags the merge commit on `main` with an annotated tag (its date is the release time
   `dora` uses) and pushes it. The snippet tags the last commit on `main`'s first-parent line that changed the
   `version` line in `package.json` (the release merge, even if other PRs merged after it), takes the version from
   that commit, and stops if the tag already exists or any step fails:

   ```sh
   (
     set -e
     git switch main
     git pull --ff-only
     sha="$(git log -1 --first-parent -G'"version"' --format=%H -- package.json)"
     v="v$(git show "$sha:package.json" | node -p 'JSON.parse(require("fs").readFileSync(0, "utf8")).version')"
     if git rev-parse -q --verify "refs/tags/$v" >/dev/null ||
       git ls-remote --exit-code --tags origin "refs/tags/$v" >/dev/null; then
       echo "$v is already tagged: has the release PR merged?" >&2
       exit 1
     fi
     git tag -a "$v" "$sha" -m "$v"
     git push origin "$v"
   )
   ```

3. `.github/workflows/release.yml` runs two jobs:
   - `verify`, with no publishing rights: the tag matches `package.json` and is on `main`, the version isn't on
     npm yet (so a re-tag fails early), then the tests and the package check.
   - `publish`, in the `npm-release` environment: installs a pinned npm (checked against its sha512 integrity),
     then `npm publish --access public` with [npm trusted publishing](https://docs.npmjs.com/trusted-publishers)
     (OIDC, `id-token: write`): no npm token is stored or passed, and npm adds provenance automatically.
     Prereleases (`1.2.3-rc.1`) go to the `next` dist-tag.

Pushing the tag is the approval only if nobody else can push one or publish. Set up once:

- **Trusted publisher** (npmjs.com → the package's Settings → Trusted publishing): GitHub Actions, repository
  `jtouley/cadence-orchestrator`, workflow `release.yml`, environment `npm-release`. Trusted publishing needs
  npm 11.5.1 or later (the workflow pins 11.21.1), Node 22.14.0 or later and a GitHub-hosted runner.
- **Environment** `npm-release` (Settings → Environments): add the owner as a required reviewer and limit its
  deployment tags to `v*`. It holds no npm token.
- **Tag ruleset** (Settings → Rules → Rulesets, target tags `v*`): restrict creation, update and deletion to the
  owner.

### Switching to trusted publishing

The trusted publisher is pending validation until it publishes once, which must happen before 2026-11-04 21:13 UTC.
Make the first OIDC release a prerelease (for example `v0.1.6-rc.0`), so it goes to `next` and leaves `latest`
alone if something is wrong. After it succeeds, the owner locks down token publishing:

1. On npmjs.com, the package's Settings → **Publishing access** → **Require two-factor authentication and disallow
   tokens**. This doesn't affect the trusted publisher.
2. Delete the `NPM_TOKEN` secret from the `npm-release` environment (Settings → Environments → `npm-release`).

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
