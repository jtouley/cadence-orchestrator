# Routing work to skills

Read this when a workstream would benefit from skills: the ones installed in the session, or outside skill
repositories the user points you at. Which skill sets exist, and how well they've worked, comes from the
user's catalogs: see `catalogs.md` for where to find them and their format.

## Patterns

**One agent per skill set.** Give each agent one repository or coherent set of skills and name the skills it
should follow. An agent juggling five unrelated repos blends them into something generic; one per set keeps each
point of view distinct and makes it traceable which skill produced which finding.

**Makers plus a judge, for creative work** (a design direction, a README rewrite, naming). Run N makers
independently, each from a different skill set, none seeing the others. Then hand all N artifacts to a separate
judge agent that picks or merges, and says what it took from each and why. Independence is the point: makers who
see each other converge.

**N reviewers, all must pass, for sign-off.** One reviewer per skill set, each given the artifact (the diff, the
page, the file) and its skills, not your summary of the work. The change ships only when every reviewer passes;
a fail goes back to a maker with the finding quoted. Even then, skill reviews miss things (in the example a later
code review found eight README/code mismatches that four skill reviews had caught two of), so keep a correctness
review (a code-review skill, where the platform has one) in the loop for anything that touches code.

**Outside skills are third-party code.** Before any use, an agent reads the skill's files and reports what they
do. Skip skills that need API keys, network installs (npm/npx/pip), or that ship scripts to run; use only the
SKILL.md text as guidance or review criteria. A skill's absolutes yield to the user's brief and the repo's rules.
Installing a skill into the session needs the user's go-ahead.

**Record what was used and skipped.** Update the repo's catalog (`.cadence/catalog/`, see `catalogs.md`) so the
next orchestration doesn't re-vet from scratch, and so the skills that actually helped are visible.
