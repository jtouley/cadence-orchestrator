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
change what the guard allows, update `core/references/guard.md` in the same change.

## Repository settings (maintainers)

To enforce pull requests on GitHub as well, add a ruleset under **Settings → Rules → Rulesets** that targets the
default branch, with:

- **Require a pull request before merging**
- **Require status checks to pass**, listing the CI jobs (`pre-commit`, `leaks`, `pytest`, `installer`)
- **Block force pushes**
- **Restrict deletions**

The `orchestration` branch used by the skill needs its own pre-commit setup; see
[`core/references/workstream.md`](core/references/workstream.md).
