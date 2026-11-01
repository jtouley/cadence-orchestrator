# Outside skills we've used (example catalog)

Owner: jtouley · Covers: app design, the public site, READMEs, dbt and DuckDB data work · Updated: 2026-10

> **One user's catalog, shipped as an example.** It reflects the coffee-data-tracker projects and that user's
> needs, and may not fit yours. Put your own catalog in `.cadence/catalog/` (see `catalogs.md`). Use this one
> for routing only if the user confirms it fits.

Each skill came from someone else's repository and was read before use, as third-party code. Skills that needed
API keys, network installs or scripts were skipped. Issue and PR numbers (#14, #35, ...) refer to the
coffee-data-tracker repository.

## Design: Emil Kowalski

- **Source**: [github.com/emilkowalski/skills](https://github.com/emilkowalski/skills)
- **Use for**: motion and interaction design in apps
- **Skills**:
  - `apple-design`: motion and interaction (respond on press, interruptible springs, system type). DESIGN.md,
    #35, #38.
  - `emil-design-eng`, `mobile-native`: read alongside apple-design for the app direction. DESIGN.md.
  - `animate-expo`: Skipped: needs npm/npx installs.
- **Rating**: 3.5/5. Set the app's motion and press feel. One designer run didn't finish.

## Design: ConardLi garden-skills

- **Source**: [github.com/ConardLi/garden-skills](https://github.com/ConardLi/garden-skills)
- **Use for**: design-system audits and visual direction
- **Skills**:
  - `web-design-engineer`: the "Group Head" direction (a Braun-style control panel, hairlines, one brown signal).
    Its Dieter Rams recipe fed Bench Scale. DESIGN.md, #35, #38.
  - `gpt-image-2`: Skipped: needs an image API key.
- **Rating**: 3.5/5. A sharp systems auditor (22 font sizes, off-grid spacing). Its own look was mostly rejected.

## Design: Elaya Design

- **Source**: [github.com/elayadesign/ai-design-skills](https://github.com/elayadesign/ai-design-skills)
- **Use for**: landing pages, conversion and information architecture
- **Skills**:
  - `landing-page-design`: conversion and information-architecture rules for the beta call to action. Not
    applied: its absolutes (Geist only, gradient hero text, word-reveal), which conflict with Bench Scale and the
    CSP. DESIGN.md, #35, #38.
- **Rating**: 3/5. Useful on flows (the invite landing, the product name). Its visual absolutes clashed with the
  brief and were overruled most often.

## Design: Meng To

- **Source**: [github.com/MengTo/Skills](https://github.com/MengTo/Skills)
- **Use for**: a craft bar for sites; catching generic, AI-looking design
- **Skills**:
  - `build-awwwards-quality-sites`: the craft bar for the site. Not applied: its GSAP/Three.js stack. DESIGN.md,
    #35, #38.
  - `no-ai-design-slop`, `audit-ai-design-slop`: checks for generic, AI-looking design; used on the README and
    the reading animation. #14, #35, #38.
  - `elevenlabs-tts`, `codex-gpt-image-2-5-flare`, `write-like-meng-on-x`, game and illustration skills: Skipped:
    API keys, a tweet corpus or Node scripts.
- **Rating**: 4/5. Strong for design (one authored moment, no tracked caps), middling on README prose.

## Design: Jakub Krehel

- **Source**: [github.com/jakubkrehel/skills](https://github.com/jakubkrehel/skills)
- **Use for**: UI critique, visual detail and copy
- **Skills**:
  - `interface-review`: UI critique of the site and app. #35, #38.
  - `better-interface`, `better-ui`, `better-colors`, `better-typography`: the app's visual details, e.g. chart
    text moved from 3.5:1 to 6.5:1 contrast. DESIGN.md.
  - `better-writing`: concise, specific labels in the app; one of the README reviewers. DESIGN.md, #14.
- **Rating**: 4/5 for the UI set (found the unannounced notice and contrast fixes; Bench Scale came partly from
  it). `better-writing` 4/5: a dependable copy editor, 11 of 12 README findings applied; copy only.

## Design: Owl-Listener designer-skills

- **Source**: [github.com/Owl-Listener/designer-skills](https://github.com/Owl-Listener/designer-skills)
- **Use for**: navigation, brand consistency, heuristic evaluation, UI principles
- **Skills**:
  - `navigation-patterns`, `critique-brand-consistency`, `heuristic-evaluation`: the site/app navigation and
    one-brand review. #35, #38.
  - `color-system`, `dark-mode-design`, `typography-scale`, `fitts-law`, `form-design`, `gesture-patterns`,
    `feedback-patterns`, `interfaces-that-feel`: UI and interaction principles behind the app's direction.
    DESIGN.md.
  - `scripts/*.py`, `build-gemini.sh`: Skipped: scripts.
- **Rating**: 4.5/5. The best design reviewer. It caught a stale prefilled shot time that fed the advice, and its
  ratio bar, taste mark and 5 s undo shipped.

## README: good-readme (Ade Oshineye)

- **Source**: [github.com/adewale/good-readme](https://github.com/adewale/good-readme)
- **Use for**: README structure and accuracy
- **Skills**:
  - `good-readme`: one of the two rewrites and a reviewer in #14.
- **Rating**: 4.5/5. The most useful. Its README audit found three real code bugs (grind direction,
  `make init --public`, the facts-only guardrail), all fixed.

## README: readme-roast

- **Source**: [github.com/hidai25/readme-roast](https://github.com/hidai25/readme-roast)
- **Use for**: a critical README audit
- **Skills**:
  - `readme-roast`: with its readme-audit, hero, install, structure and star-killers sub-skills; the other
    rewrite and a reviewer in #14.
- **Rating**: 3.5/5. Good on structure and install steps. It pushed growth-hacking (star asks, invented timings)
  that was rejected.

## Data: dbt Labs dbt-agent-skills

- **Source**: [github.com/dbt-labs/dbt-agent-skills](https://github.com/dbt-labs/dbt-agent-skills) (cloned
  read-only; SKILL.md files used as review criteria)
- **Use for**: dbt modeling, testing and documentation reviews
- **Skills**:
  - `adding-dbt-unit-test`: behind the unit tests for the suspect-run and price-event macros. #49. Rating 4.5/5:
    the best data skill. It kept unit tests out of the weekly build, where they would have failed every release,
    and led to the testable macros. Merged.
  - `using-dbt-for-analytics-engineering`: modeling, materialization and testing practice, with its
    writing-data-tests reference. #36, #49. Rating 3/5: found real drift in the wholesale filter (fixed in #37,
    still open); its sources finding wasn't built.
  - `maintaining-dbt-documentation`: #49. Rating 1.5/5: its one finding (synced column docs, provenance fields)
    wasn't built.
  - `running-dbt-commands`, `using-dbt-state`: in the review brief for #49; no traceable effect.

## Data: wshobson agents

- **Source**: [github.com/wshobson/agents](https://github.com/wshobson/agents) (data-engineering plugin)
- **Use for**: dbt transformation layering and data-quality checks
- **Skills**:
  - `dbt-transformation-patterns`: #36, #49. Rating 3.5/5: one rule for a passing build, read through staging.
    Merged.
  - `data-quality-frameworks`: #36, #49. Rating 2/5: its median baseline clashed with approving real changes.
    Blocked in review and reverted.

## Data: DuckDB duckdb-skills

- **Source**: [github.com/duckdb/duckdb-skills](https://github.com/duckdb/duckdb-skills)
- **Use for**: the DuckDB command line
- **Skills**:
  - `duckdb-skills`: official, but mostly about using the CLI, with little best-practice content. #49.
- **Rating**: 1/5. Nothing traceable to it. The ordered export came from DuckDB's docs instead
  ([file formats](https://duckdb.org/docs/stable/guides/performance/file_formats),
  [Parquet tips](https://duckdb.org/docs/stable/data/parquet/tips)).

## Data: MotherDuck agent-skills

- **Source**: [github.com/motherduckdb/agent-skills](https://github.com/motherduckdb/agent-skills)
- **Use for**: DuckDB pipelines, modeling and loading
- **Skills**:
  - `build-data-pipeline`, `model-data`, `load-data`: DuckDB pipeline, modeling and loading practice. #49.
- **Rating**: 4/5. Staging tables and NOT NULL constraints both merged, with identical output on the real lake.
  About 4% slower on the real build.

## Track record

| Work | Skills | Outcome |
| --- | --- | --- |
| App design direction (`docs/app/DESIGN.md`, "Bench Scale") | Six designers, one per repo, each following that repo's skills | The result became Bench Scale |
| README rewrite (#14) | `readme-roast`, `good-readme` (two rewrites merged by a judge); reviewed with `readme-roast`, `good-readme`, `better-writing`, `no-ai-design-slop` | Merged. A later code review still found eight README/code mismatches; the skills had caught two |
| Public site and app review (#35) | `landing-page-design`, `build-awwwards-quality-sites`, `audit-ai-design-slop`, `interface-review`, `navigation-patterns`, `critique-brand-consistency`, `heuristic-evaluation` | Findings applied (see ratings) |
| Reading animation sign-off (#38, #44) | Six independent reviews, one per repo | All passed |
| dbt hardening (#49) and the earlier dbt/Great Expectations review (#36) | dbt Labs, wshobson, DuckDB and MotherDuck sets as review criteria | See the data ratings; #36 wasn't traced finding by finding |

Ratings come from what happened to each skill's work in the PRs and session records: output quality (including
real bugs found), how much was kept rather than rejected or reverted, and whether it changed decisions rather than
only checking them. Evidence is thinner for the app-milestone design reviews (#15 to #21), rated from PR text and
DESIGN.md rather than per-reviewer reports.

## Install status

Nine of the vetted skills were installed into the design session's `~/.claude/skills` with the user's go-ahead:
`apple-design`, `web-design-engineer`, `landing-page-design`, `build-awwwards-quality-sites`,
`audit-ai-design-slop`, `interface-review`, `navigation-patterns`, `critique-brand-consistency` and
`heuristic-evaluation`. They lived in that session's container, not in the repo, so a new session has to install
them again.
