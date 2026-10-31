# Skill catalogs

A catalog tells you which skill sets exist for this user or environment, what each is good for, and how well it
has worked. Catalogs are pluggable because no single list fits everyone: each repo, user or environment brings
its own. The one shipped here (`example-registry.md`) is one user's catalog, kept as an example.

## Lookup order

Use every catalog found in the first two places. Fall back to the shipped example only when there are none.

1. **Repo**: `.cadence/catalog/*.md` in the target repo. Works in cloud sessions, because it's committed.
2. **User**: each directory in `$CADENCE_CATALOG_PATH` (colon-separated), or `~/.cadence/catalog/*.md` if it isn't
   set. Not present in most cloud sessions.
3. **Shipped example**: `references/example-registry.md`. It reflects one user's projects and needs. Use it to
   see the format, or for routing only if the user confirms it fits.

When two catalogs describe the same skill set (the same `##` heading), the earlier source wins: the repo
overrides the user, and the user overrides the example. Use Glob and Read to list and read them; they're
documents, so reading them is allowed. In the workstream doc, say which catalog each routing choice came from.

To add one, write a file in the format below to `.cadence/catalog/` (commit it) or `~/.cadence/catalog/`.
`install.sh --catalog <file>` copies a file into the repo's catalog folder.

## Format

Plain markdown, one file per catalog, for people to edit and models to read. Each skill-set section needs
`Source` and `Skills`; everything else, including the track record, is optional.

```markdown
# <catalog title>

Owner: <person or team> · Covers: <kinds of work> · Updated: <YYYY-MM-DD>

## <skill set name>

- **Source**: <repository URL, or where it's installed>
- **Use for**: <kinds of work it helps with>
- **Skills**:
  - `skill-a`: what it was used for. Not applied: <its rules that conflicted with the brief>.
  - `skill-b`: Skipped: needs an API key.
- **Rating**: 4/5. <what its work led to, with a link to the evidence>

## Track record

| Work | Skills | Outcome |
| --- | --- | --- |
| <task, with a PR link> | skill-a, skill-b | <kept, rejected or reverted, and why> |
```

Rate from what happened to the work (kept, rejected, reverted, bugs found), not from how the output read. Say
when the evidence is thin. Record skipped skills and why, so the next orchestration doesn't re-vet them.
