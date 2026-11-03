// `cadence-orchestrator dora`: DORA's five software delivery metrics, read-only.
//
// Definitions are DORA's (https://dora.dev/guides/dora-metrics/). Deploys come from release tags (v*, default),
// changes landing on main (`--deploys merges`), or versions published to npm (`--deploys npm`, network, the
// most faithful when the package is on npm). Failures come only from explicit records: CHANGELOG
// "### Fixed (regression from X.Y.Z)" subsections and tasks.json entries with kind "fix" and a version in
// `fixes`. Without records, or when records can't be matched to deploys, it says so instead of guessing.

import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const DEFINITIONS = {
  deployment_frequency: "The number of deployments over a given period or the time between deployments.",
  change_lead_time:
    "The amount of time it takes for a change to go from committed to version control to deployed in production.",
  change_fail_rate: "The ratio of deployments that require immediate intervention following a deployment.",
  deployment_rework_rate:
    "The ratio of deployments that are unplanned but happen as a result of an incident in production.",
  failed_deployment_recovery_time:
    "The time it takes to recover from a deployment that fails and requires immediate intervention.",
};
const FEW_DEPLOYS = 10;
// A per-week rate is shown only over a window of at least 4 weeks: over a few days it extrapolates a burst of
// releases into a weekly figure that changes with the time the command runs.
const MIN_RATE_DAYS = 28;
const MIN_FAILURES = 3; // fewer recorded failures make fail rate, rework and recovery time anecdotes
const GUIDE = "https://dora.dev/guides/dora-metrics/";
// Paraphrases DORA's guide, which says: "The goal is to improve your team’s performance over time, not to compete
// against other teams or organizations."; broad targets increase "the likelihood that teams will try to game the
// metrics."; "Comparing metrics between vastly different applications (for example, a mobile app and a mainframe
// system) can be misleading."; and warns against "Attempting to measure complex systems with the idea that only one
// metric matters." The small-sample rules (FEW_DEPLOYS, MIN_FAILURES, MIN_RATE_DAYS) are this tool's, not the guide's.
const CAUTION =
  `Per DORA's guide (${GUIDE}): read the five together, as your team's trend over time; ` +
  "not as targets, and not to rank teams or compare very different apps.";
// Shared with skills/tpm/scripts/tasks_check.py (ISO8601, SEMVER); a test keeps the patterns identical.
const ISO8601 = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d{3}|\.\d{6})?)?(Z|[+-]\d{2}:\d{2})$/;
const SEMVER = /^v?\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/;
const bare = (v) => v.replace(/^v/, "");
const isPlaceholder = (v) => /^0\.0\.0(-|$)/.test(v);
const isPrerelease = (v) => v.includes("-");
// The one production-deploy rule: placeholders (0.0.0*) never count; prereleases only with --include-prereleases.
const countsAsDeploy = (v, includePrereleases) => !isPlaceholder(v) && (includePrereleases || !isPrerelease(v));

export function parseTime(value) {
  // Seconds since the epoch, or null when the value doesn't follow the shared ISO 8601 rule or names an
  // impossible date or time (2026-02-30, 24:00). The fields are checked by a round trip, as Python does.
  if (typeof value !== "string" || !ISO8601.test(value)) return null;
  const m = value.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?(Z|([+-])(\d{2}):(\d{2}))$/);
  const [y, mo, d, h, mi, s] = m.slice(1, 7).map((x) => Number(x ?? 0));
  const local = new Date(Date.UTC(y, mo - 1, d, h, mi, s));
  const sameFields =
    local.getUTCFullYear() === y && local.getUTCMonth() === mo - 1 && local.getUTCDate() === d &&
    local.getUTCHours() === h && local.getUTCMinutes() === mi && local.getUTCSeconds() === s;
  if (!sameFields || (m[7] !== "Z" && (Number(m[9]) > 23 || Number(m[10]) > 59))) return null;
  const ms = Date.parse(value);
  return Number.isNaN(ms) ? null : ms / 1000;
}

const git = (repo, args) =>
  execFileSync("git", ["-C", repo, ...args], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
const lines = (s) => (s ? s.split("\n") : []);

// Release tags v*, listed once: name, version, commit, time (the tagger date, or the commit's for a lightweight tag).
function listTags(repo) {
  const out = git(repo, [
    "for-each-ref",
    "refs/tags/v*",
    "--format=%(refname:short)\t%(objecttype)\t%(*objectname)\t%(objectname)\t%(taggerdate:unix)\t%(creatordate:unix)",
  ]);
  const tags = [];
  for (const l of lines(out)) {
    const [name, type, peeled, obj, taggerDate, creatorDate] = l.split("\t");
    if (!SEMVER.test(name)) continue;
    const annotated = type === "tag";
    tags.push({
      name,
      version: bare(name),
      commit: annotated ? peeled : obj,
      time: Number(annotated ? taggerDate : creatorDate),
      annotated,
    });
  }
  return tags;
}

function deploysFromTags(repo, warnings) {
  const tags = listTags(repo);
  const lightweight = tags.filter((t) => !t.annotated).length;
  const deploys = tags.map(({ name, version, commit, time }) => ({ name, version, commit, time }));
  if (lightweight) {
    warnings.push(
      `${lightweight} lightweight tag(s): their commit's date is used as the deploy time. Use annotated tags ` +
        "(git tag -a), whose tagger date is the release time.",
    );
  }
  return deploys;
}

function deploysFromMerges(repo) {
  // origin/main when there is one (a local main can be stale), else main, else HEAD.
  const branch =
    ["origin/main", "main"].find((ref) => {
      try {
        git(repo, ["rev-parse", "--verify", "--quiet", ref]);
        return true;
      } catch {
        return false;
      }
    }) ?? "HEAD";
  return lines(git(repo, ["log", "--first-parent", "--format=%H %ct", branch])).map((l) => {
    const [commit, time] = l.split(" ");
    return { name: commit.slice(0, 7), version: null, commit, time: Number(time) };
  });
}

function npmTimes(repo, warnings) {
  // `npm view <pkg> time --json`. CADENCE_DORA_NPM_TIMES (a JSON file) stands in for the network in tests.
  if (process.env.CADENCE_DORA_NPM_TIMES) return JSON.parse(fs.readFileSync(process.env.CADENCE_DORA_NPM_TIMES, "utf8"));
  let name = "";
  try {
    name = JSON.parse(fs.readFileSync(path.join(repo, "package.json"), "utf8")).name;
  } catch {}
  if (!name) {
    warnings.push("--deploys npm needs a package.json with a name.");
    return {};
  }
  const r = spawnSync("npm", ["view", name, "time", "--json"], { encoding: "utf8" });
  if (r.status !== 0) {
    warnings.push(`npm view ${name} time failed: ${(r.stderr || r.error?.message || "").trim().split("\n").at(-1)}`);
    return {};
  }
  return JSON.parse(r.stdout);
}

// Returns the published versions as deploys, and the release tags (listed once) for the unpublished-tag check.
function deploysFromNpm(repo, warnings) {
  const times = npmTimes(repo, warnings);
  const tags = listTags(repo);
  const tagged = new Map(tags.map((t) => [t.version, t.commit]));
  const deploys = [];
  const unmapped = [];
  for (const [version, iso] of Object.entries(times)) {
    if (!SEMVER.test(version)) continue; // skips "created" and "modified"
    const time = Date.parse(iso) / 1000;
    let commit = tagged.get(version) ?? "";
    if (!commit) {
      // No tag: the first commit whose package.json has this version.
      const hits = lines(git(repo, ["log", "--format=%H", "--reverse", "-S", `"version": "${version}"`, "--", "package.json"]));
      commit = hits[0] ?? "";
    }
    if (!commit && countsAsDeploy(version, false)) unmapped.push(version);
    deploys.push({ name: version, version, commit: commit || null, time });
  }
  if (unmapped.length) {
    warnings.push(`npm versions with no matching commit (no tag or package.json change): ${unmapped.join(", ")}`);
  }
  return { deploys, tags, published: Object.keys(times).length > 0 };
}

function changelogFixes(repo) {
  // { fixingVersion, failedVersion } from "## X.Y.Z" sections with "### Fixed (regression from A.B.C)".
  const file = path.join(repo, "CHANGELOG.md");
  if (!fs.existsSync(file)) return [];
  const fixes = [];
  let section = null;
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    if (/^##\s/.test(line)) {
      const h2 = line.match(/^##\s+(v?\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)\s*$/);
      section = h2 ? bare(h2[1]) : null; // any other "## " heading resets it
    }
    const fixed = line.match(/^###\s+Fixed \(regression from (v?\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)\)/);
    if (fixed && section) fixes.push({ failedVersion: bare(fixed[1]), fixingVersion: section, source: "CHANGELOG.md" });
  }
  return fixes;
}

function taskFixes(repo, warnings) {
  // tasks.json entries: kind "fix", fixes "<version>", deployed_at optional.
  const out = [];
  for (const dir of ["workstreams", path.join(".cadence", "workstreams")]) {
    const full = path.join(repo, dir);
    if (!fs.existsSync(full)) continue;
    for (const name of fs.readdirSync(full).filter((n) => n.endsWith(".tasks.json"))) {
      const file = path.join(dir, name);
      let data;
      try {
        data = JSON.parse(fs.readFileSync(path.join(full, name), "utf8"));
      } catch (e) {
        warnings.push(`${file} isn't valid JSON (${e.message}); its fix records are ignored`);
        continue;
      }
      for (const t of data?.tasks ?? []) {
        if (t?.kind !== "fix" || typeof t.fixes !== "string" || !SEMVER.test(t.fixes)) continue;
        const fixedAt = t.deployed_at == null ? null : parseTime(t.deployed_at);
        if (t.deployed_at != null && fixedAt === null) {
          warnings.push(`${file}: task ${t.id}: deployed_at ${JSON.stringify(t.deployed_at)} isn't ISO 8601 with a timezone`);
        }
        const fixedIn = typeof t.fixed_in === "string" && SEMVER.test(t.fixed_in) ? bare(t.fixed_in) : null;
        out.push({ failedVersion: bare(t.fixes), fixedAt, fixedIn, source: file, task: t.id });
      }
    }
  }
  return out;
}

// Min, median and max from one sorted copy (no argument spreading, which overflows the stack on huge arrays).
export function intervalStats(gaps) {
  if (!gaps.length) return null;
  const s = [...gaps].sort((a, b) => a - b);
  return { min: s[0], median: median(s), max: s.at(-1) };
}

const median = (xs) => {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};
const p90 = (xs) => (xs.length ? [...xs].sort((a, b) => a - b)[Math.ceil(0.9 * xs.length) - 1] : null);
const human = (seconds) => {
  if (seconds === null) return "n/a";
  const h = seconds / 3600;
  return h < 48 ? `${h.toFixed(1)} h` : `${(h / 24).toFixed(1)} days`;
};
const pct = (a, n) => `${a}/${n} deploys (${((100 * a) / n).toFixed(0)}%)`;

export function dora(
  repo,
  { since = null, deploys: mode = "tags", includePrereleases = false, now = Date.now() / 1000 } = {},
) {
  const warnings = [];
  const source = {
    tags: "git: release tags v* (annotated: tagger date)",
    merges: "git: first-parent commits on main (origin/main if present; each change landing on main)",
    npm: "npm registry: publish time of each version (npm view <package> time)",
  }[mode];
  const npm = mode === "npm" ? deploysFromNpm(repo, warnings) : null;
  const loaded = mode === "merges" ? deploysFromMerges(repo) : npm ? npm.deploys : deploysFromTags(repo, warnings);
  const excluded = loaded.filter((d) => d.version && !countsAsDeploy(d.version, includePrereleases));
  if (excluded.length) {
    warnings.push(
      `Not counted as deploys: ${excluded.map((d) => d.version).join(", ")} (0.0.0 placeholders` +
        (includePrereleases ? ")" : " and prereleases; --include-prereleases counts prereleases)"),
    );
  }
  const all = loaded.filter((d) => !excluded.includes(d)).sort((a, b) => a.time - b.time);
  if (mode === "tags" && all.length) {
    warnings.push("Tag mode counts every v* tag, even one whose release failed; --deploys npm counts only published versions.");
  }
  const start = since ? since.getTime() / 1000 : all.length ? all[0].time : now;
  const inWindow = all.filter((d) => d.time >= start && d.time <= now);
  const metrics = {};
  // npm mode, the other direction: release tags in the window with no npm version (a failed publish, say).
  const npmVersions = new Set(loaded.map((d) => d.version));
  const unpublished = npm?.published
    ? npm.tags
        .filter((t) => !npmVersions.has(t.version) && countsAsDeploy(t.version, includePrereleases))
        .filter((t) => t.time >= start && t.time <= now)
        .sort((a, b) => a.time - b.time)
        .map((t) => t.name)
    : [];
  for (const t of unpublished) warnings.push(`${t} is tagged but was never published to npm; not counted.`);

  if (!inWindow.length) {
    warnings.push(
      { tags: "No release tags (v*) in this window. Tag releases, or use --deploys merges or npm.", merges: "No commits on main in this window.", npm: "No published versions in this window." }[mode],
    );
  }

  // Deployment frequency: the actual count and the span they cover. A per-week rate only over a window of at least
  // MIN_RATE_DAYS (counted from the window start to now); with few deploys, the real intervals (min, median, max).
  const weeks = Math.max(now - start, 3600) / (7 * 86400);
  const windowDays = (now - start) / 86400;
  const gaps = inWindow.slice(1).map((d, i) => d.time - inWindow[i].time);
  const span = inWindow.length > 1 ? inWindow.at(-1).time - inWindow[0].time : null;
  const rateShown = windowDays >= MIN_RATE_DAYS;
  const intervals = intervalStats(gaps);
  // The guide: "The number of deployments over a given period or the time between deployments." The period is the
  // window the rate uses: --since (or the first deploy) to now.
  let value = "not measurable: no deploys";
  if (inWindow.length) {
    const from = since ? "--since" : "first deploy";
    value =
      `${inWindow.length === 1 ? "1 deploy" : `${inWindow.length} deploys`} in ${human(now - start)} (${from} to now)` +
      (span !== null ? `; first to last deploy ${human(span)}` : "") +
      (rateShown
        ? `; ${(inWindow.length / weeks).toFixed(1)}/week`
        : `; no weekly rate (this tool shows one only over ${MIN_RATE_DAYS / 7} weeks or more)`);
    if (intervals) {
      value +=
        inWindow.length < FEW_DEPLOYS
          ? `; intervals min ${human(intervals.min)}, median ${human(intervals.median)}, max ${human(intervals.max)}`
          : `; median interval ${human(intervals.median)}`;
    }
  }
  metrics.deployment_frequency = {
    value,
    count: inWindow.length,
    per_week: rateShown ? inWindow.length / weeks : null,
    per_week_shown: rateShown,
    min_rate_window_days: MIN_RATE_DAYS,
    span_seconds: span,
    median_seconds_between: median(gaps),
    intervals_seconds: intervals,
    window: { start, end: now },
    sample: inWindow.length,
    source:
      `${source}; window from ${since ? "--since" : "the first deploy"} to now; this tool shows a weekly rate only ` +
      `over a window of ${MIN_RATE_DAYS} days or more`,
  };

  // Change lead time: each commit counts against the first deploy containing it, and no earlier deploy (by
  // ancestry, so out-of-order or maintenance tags don't double count). Commits older than the window start are
  // the baseline, not measured.
  const leads = [];
  let baseline = 0;
  let skewed = 0;
  for (const d of inWindow) {
    if (!d.commit) continue;
    // Tags and npm versions can be out of order (maintenance releases), so exclude every earlier deploy.
    // Merges are main's linear first-parent history, where the previous deploy alone is enough.
    const before = all.filter((e) => e.time < d.time && e.commit);
    const earlier = mode === "merges" ? before.slice(-1).map((e) => e.commit) : before.map((e) => e.commit);
    const out = git(repo, ["log", "--no-merges", "--format=%ct", d.commit, ...(earlier.length ? ["--not", ...earlier] : [])]);
    for (const l of lines(out)) {
      const committed = Number(l);
      if (committed < start) baseline += 1;
      else if (committed > d.time) skewed += 1;
      else leads.push(d.time - committed);
    }
  }
  metrics.change_lead_time = {
    value:
      (leads.length ? `median ${human(median(leads))}, p90 ${human(p90(leads))}` : "not measurable: no deployed commits in the window") +
      (baseline ? `; ${baseline} older commit(s) are the baseline, not measured` : "") +
      (skewed ? `; ${skewed} commit(s) dated after their deploy were skipped` : ""),
    median_seconds: median(leads),
    p90_seconds: p90(leads),
    baseline_commits: baseline,
    sample: leads.length,
    source:
      `${source}; commit time is the committer date, which a rebase, amend or squash resets ` +
      "(shortening lead time)",
  };

  // Instability, from explicit failure records only, de-duplicated per failed version.
  const records = [...changelogFixes(repo), ...taskFixes(repo, warnings)];
  const recordSources = 'CHANGELOG.md "### Fixed (regression from X.Y.Z)"; tasks.json kind "fix" with a version in fixes';
  const keys = ["change_fail_rate", "deployment_rework_rate", "failed_deployment_recovery_time"];
  let failures = 0; // recorded failures matched to deploys in the window
  const unmeasurable = (why) => ({ value: `not measurable: ${why}`, sample: 0, source: recordSources });
  if (!records.length) {
    for (const k of keys) metrics[k] = unmeasurable("no failure records");
  } else if (mode === "merges") {
    for (const k of keys) metrics[k] = unmeasurable("failure records name versions, which --deploys merges can't match to deploys");
  } else {
    const byVersion = new Map(all.map((d) => [d.version, d]));
    const windowVersions = new Set(inWindow.map((d) => d.version));
    const failedAll = [...new Set(records.map((r) => r.failedVersion))];
    const unmatchedFailures = failedAll.filter((v) => !byVersion.has(v));
    const failedVersions = failedAll.filter((v) => windowVersions.has(v));
    // The deploy that shipped each fix, per failed version (the earliest wins):
    // - CHANGELOG: the release whose section lists the fix;
    // - tasks.json: the version in `fixed_in`, else the latest deploy at or before `deployed_at` (the tag comes
    //   before the publish), if it's within 48 h and isn't the failed version itself.
    const WINDOW = 48 * 3600;
    const fixOf = new Map();
    const unmatchedFixes = [];
    for (const v of failedVersions) {
      const failed = byVersion.get(v);
      const candidates = [];
      for (const r of records.filter((r) => r.failedVersion === v)) {
        let deploy = null;
        let at = null;
        if (r.fixingVersion) deploy = byVersion.get(r.fixingVersion) ?? null;
        else if (r.fixedIn) deploy = byVersion.get(r.fixedIn) ?? null;
        else if (r.fixedAt !== null && r.fixedAt !== undefined) {
          const live = all.filter((d) => d.time <= r.fixedAt).at(-1);
          if (live && live.version !== v && r.fixedAt - live.time <= WINDOW) deploy = live;
          at = r.fixedAt;
        }
        if (deploy && deploy.time >= failed.time) candidates.push({ ...deploy, time: at ?? deploy.time });
      }
      candidates.sort((a, b) => a.time - b.time);
      if (candidates.length) fixOf.set(v, candidates[0]);
      else unmatchedFixes.push(v);
    }
    const n = inWindow.length;
    failures = failedVersions.length;
    if (!n) {
      for (const k of keys) metrics[k] = unmeasurable("no deploys in the window");
    } else if (!failedVersions.length && unmatchedFailures.length) {
      for (const k of keys) {
        metrics[k] = unmeasurable(`failure records don't match any deploy here (${unmatchedFailures.join(", ")})`);
      }
    } else {
      // Never a bare percentage when some records couldn't be matched: give the counts instead.
      const matchNote = (matched, unmatched, what) =>
        `${matched} ${what} matched, ${unmatched.length} unmatched (${unmatched.join(", ")})`;
      metrics.change_fail_rate = {
        value: unmatchedFailures.length
          ? `${failedVersions.length}/${n} deploys failed; ` +
            matchNote(failedVersions.length, unmatchedFailures, "failure record(s)")
          : pct(failedVersions.length, n),
        failed: failedVersions,
        unmatched: unmatchedFailures,
        sample: n,
        source: recordSources,
      };
      const rework = new Set([...fixOf.values()].filter((f) => windowVersions.has(f.version)).map((f) => f.version));
      const unmatchedRework = [...unmatchedFixes.map((v) => `fix of ${v}`), ...unmatchedFailures];
      metrics.deployment_rework_rate = {
        value: unmatchedRework.length
          ? `${rework.size}/${n} deploys were fixes; ${matchNote(fixOf.size, unmatchedRework, "fix(es)")}`
          : pct(rework.size, n),
        rework: [...rework],
        unmatched: unmatchedRework,
        sample: n,
        source:
          `${recordSources}; the deploy that shipped each fix: the CHANGELOG release, tasks.json fixed_in, or the ` +
          "latest deploy at or before deployed_at (within 48 h)",
      };
      const recoveries = [...fixOf.entries()].map(([v, f]) => f.time - byVersion.get(v).time);
      metrics.failed_deployment_recovery_time = {
        value:
          (recoveries.length ? `median ${human(median(recoveries))}` : "not measurable: no recorded fix times") +
          (unmatchedFixes.length ? `; ${unmatchedFixes.length} failure(s) have no matched fix` : ""),
        median_seconds: median(recoveries),
        sample: recoveries.length,
        source: `${recordSources}; failed deploy → the matched fix's deploy (or its deployed_at)`,
      };
    }
  }
  for (const k of Object.keys(metrics)) metrics[k].definition = DEFINITIONS[k];
  // Small samples: fewer than FEW_DEPLOYS deploys, or instability (fail rate, rework, recovery time) from 1 or 2
  // recorded failures. With no failures recorded, those metrics say "not measurable" or 0%, not a number from one
  // data point.
  const fewDeploys = inWindow.length < FEW_DEPLOYS;
  const fewFailures = failures > 0 && failures < MIN_FAILURES;
  const smallSample = fewDeploys || fewFailures;
  const why = [
    ...(fewDeploys ? [`${inWindow.length} deploy${inWindow.length === 1 ? "" : "s"}`] : []),
    ...(fewFailures ? [`${failures} recorded failure${failures === 1 ? "" : "s"}`] : []),
  ].join(" and ");
  const caution = smallSample
    ? `CAUTION: only ${why}, a snapshot rather than a trend (this tool's threshold: fewer than ${FEW_DEPLOYS} ` +
      `deploys or ${MIN_FAILURES} recorded failures). ${CAUTION}`
    : CAUTION;
  return {
    deploys: mode,
    since: since ? since.toISOString() : null,
    warnings,
    metrics,
    caution,
    small_sample: smallSample,
    unpublished_tags: unpublished,
  };
}

export function formatDora(report) {
  const out = [];
  out.push(
    `DORA software delivery metrics (definitions: https://dora.dev/guides/dora-metrics/); deploys = ${report.deploys}` +
      (report.since ? ` since ${report.since.slice(0, 10)}` : ""),
  );
  if (report.small_sample) out.push(report.caution);
  for (const w of report.warnings) out.push(`warning: ${w}`);
  const names = {
    deployment_frequency: "Deployment frequency",
    change_lead_time: "Change lead time",
    change_fail_rate: "Change fail rate",
    deployment_rework_rate: "Deployment rework rate",
    failed_deployment_recovery_time: "Failed deployment recovery time",
  };
  for (const [k, m] of Object.entries(report.metrics)) {
    out.push("");
    out.push(`${names[k]}: ${m.value} (n=${m.sample})`);
    out.push(`  definition: ${m.definition}`);
    out.push(`  source: ${m.source}`);
  }
  if (!report.small_sample) {
    out.push("");
    out.push(report.caution);
  }
  return out;
}
