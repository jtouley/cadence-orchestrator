// `cadence-orchestrator dora`: DORA's five software delivery metrics from git, read-only.
//
// Definitions are DORA's (https://dora.dev/guides/dora-metrics/). Deploys are release tags (v*) by default, or
// changes landing on main (`--deploys merges`: main's first-parent commits). Failures come only from explicit
// records: CHANGELOG "### Fixed (regression from X.Y.Z)" subsections and tasks.json entries with
// `kind: "fix"`, `fixes: "<version>"`. Without records, the instability metrics print "not measurable"
// instead of a guess.

import { execFileSync } from "node:child_process";
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
const VERSION = /^\d+\.\d+\.\d+$/;

const git = (repo, args) => execFileSync("git", ["-C", repo, ...args], { encoding: "utf8" }).trim();
const lines = (s) => (s ? s.split("\n") : []);

function deploysFromTags(repo) {
  const out = git(repo, [
    "for-each-ref",
    "refs/tags/v*",
    "--format=%(refname:short)\t%(*objectname)\t%(objectname)\t%(creatordate:unix)",
  ]);
  return lines(out)
    .map((l) => {
      const [name, peeled, obj, time] = l.split("\t");
      return { name, version: name.slice(1), commit: peeled || obj, time: Number(time) };
    })
    .filter((d) => VERSION.test(d.version));
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

function changelogFixes(repo) {
  // { fixingVersion, failedVersion } from "## X.Y.Z" sections with "### Fixed (regression from A.B.C)".
  const file = path.join(repo, "CHANGELOG.md");
  if (!fs.existsSync(file)) return [];
  const fixes = [];
  let section = null;
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const h2 = line.match(/^##\s+v?(\d+\.\d+\.\d+)\b/);
    if (h2) section = h2[1];
    const fixed = line.match(/^###\s+Fixed \(regression from v?(\d+\.\d+\.\d+)\)/);
    if (fixed && section) fixes.push({ fixingVersion: section, failedVersion: fixed[1], source: "CHANGELOG.md" });
  }
  return fixes;
}

function taskFixes(repo) {
  // tasks.json entries: kind "fix", fixes "<version>", deployed_at optional.
  const out = [];
  for (const dir of ["workstreams", path.join(".cadence", "workstreams")]) {
    const full = path.join(repo, dir);
    if (!fs.existsSync(full)) continue;
    for (const name of fs.readdirSync(full).filter((n) => n.endsWith(".tasks.json"))) {
      try {
        const data = JSON.parse(fs.readFileSync(path.join(full, name), "utf8"));
        for (const t of data.tasks ?? []) {
          if (t?.kind === "fix" && typeof t.fixes === "string" && VERSION.test(t.fixes.replace(/^v/, ""))) {
            const at = Date.parse(t.deployed_at ?? "");
            out.push({
              failedVersion: t.fixes.replace(/^v/, ""),
              fixedAt: Number.isNaN(at) ? null : at / 1000,
              source: path.join(dir, name),
            });
          }
        }
      } catch {}
    }
  }
  return out;
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

export function dora(repo, { since = null, deploys: mode = "tags" } = {}) {
  const all = (mode === "merges" ? deploysFromMerges(repo) : deploysFromTags(repo)).sort((a, b) => a.time - b.time);
  const sinceTs = since ? since.getTime() / 1000 : -Infinity;
  const inWindow = all.filter((d) => d.time >= sinceTs);
  const warnings = [];
  const metrics = {};
  const deploySource =
    mode === "merges"
      ? "git: first-parent commits on main (origin/main if present; each change landing on main)"
      : "git: release tags v*";

  if (!inWindow.length) {
    warnings.push(
      mode === "tags"
        ? "No release tags (v*) found in this window. Tag releases, or use --deploys merges."
        : "No commits on main in this window.",
    );
  } else if (inWindow.length < FEW_DEPLOYS) {
    warnings.push(`Only ${inWindow.length} deploys: too few for stable numbers (DORA metrics need a trend).`);
  }

  // Deployment frequency
  const gaps = inWindow.slice(1).map((d, i) => d.time - inWindow[i].time);
  const spanDays = inWindow.length > 1 ? (inWindow.at(-1).time - inWindow[0].time) / 86400 : null;
  metrics.deployment_frequency = {
    value: inWindow.length
      ? `${inWindow.length} deploys` +
        (spanDays ? ` over ${spanDays.toFixed(1)} days (${((inWindow.length / spanDays) * 7).toFixed(1)}/week)` : "") +
        (gaps.length ? `; median time between deploys ${human(median(gaps))}` : "")
      : "not measurable: no deploys",
    count: inWindow.length,
    median_seconds_between: median(gaps),
    sample: inWindow.length,
    source: deploySource,
  };

  // Change lead time: each commit to the first deploy that contains it.
  const leads = [];
  for (const d of inWindow) {
    const i = all.indexOf(d);
    const range = i > 0 ? `${all[i - 1].commit}..${d.commit}` : d.commit;
    for (const l of lines(git(repo, ["log", "--no-merges", "--format=%ct", range]))) leads.push(d.time - Number(l));
  }
  metrics.change_lead_time = {
    value: leads.length ? `median ${human(median(leads))}, p90 ${human(p90(leads))}` : "not measurable: no deployed commits",
    median_seconds: median(leads),
    p90_seconds: p90(leads),
    sample: leads.length,
    source: `${deploySource}; commit times from git (committed → first deploy containing it)`,
  };

  // Instability: only from explicit failure records.
  const records = [...changelogFixes(repo), ...taskFixes(repo)];
  const unmeasurable = (why, sources) => ({ value: `not measurable: ${why}`, sample: 0, source: sources });
  const recordSources = "CHANGELOG.md \"### Fixed (regression from X.Y.Z)\"; tasks.json kind \"fix\", fixes \"<version>\"";
  if (!records.length) {
    for (const k of ["change_fail_rate", "deployment_rework_rate", "failed_deployment_recovery_time"]) {
      metrics[k] = unmeasurable("no failure records", recordSources);
    }
  } else if (mode !== "tags") {
    for (const k of ["change_fail_rate", "deployment_rework_rate", "failed_deployment_recovery_time"]) {
      metrics[k] = unmeasurable("failure records name versions, which --deploys merges can't match to deploys", recordSources);
    }
  } else {
    const byVersion = new Map(all.map((d) => [d.version, d]));
    const windowVersions = new Set(inWindow.map((d) => d.version));
    const failed = new Set(records.map((r) => r.failedVersion).filter((v) => windowVersions.has(v)));
    const fixing = new Set(
      records.filter((r) => r.fixingVersion && windowVersions.has(r.fixingVersion)).map((r) => r.fixingVersion),
    );
    const n = inWindow.length;
    metrics.change_fail_rate = {
      value: n ? `${failed.size}/${n} deploys (${((100 * failed.size) / n).toFixed(0)}%)` : "not measurable: no deploys",
      failed: [...failed],
      sample: n,
      source: recordSources,
    };
    metrics.deployment_rework_rate = {
      value: n ? `${fixing.size}/${n} deploys (${((100 * fixing.size) / n).toFixed(0)}%)` : "not measurable: no deploys",
      rework: [...fixing],
      sample: n,
      source: "CHANGELOG.md: deploys whose section has \"### Fixed (regression from X.Y.Z)\"",
    };
    const recoveries = [];
    for (const v of failed) {
      const start = byVersion.get(v).time;
      const ends = records
        .filter((r) => r.failedVersion === v)
        .map((r) => (r.fixingVersion ? byVersion.get(r.fixingVersion)?.time : r.fixedAt))
        .filter((t) => typeof t === "number" && t >= start);
      if (ends.length) recoveries.push(Math.min(...ends) - start);
    }
    metrics.failed_deployment_recovery_time = {
      value: recoveries.length ? `median ${human(median(recoveries))}` : "not measurable: no recorded fix deploys",
      median_seconds: median(recoveries),
      sample: recoveries.length,
      source: `${recordSources}; failed deploy → first deploy (or deployed_at) that fixes it`,
    };
  }
  for (const k of Object.keys(metrics)) metrics[k].definition = DEFINITIONS[k];
  return { deploys: mode, since: since ? since.toISOString() : null, warnings, metrics };
}

export function formatDora(report) {
  const out = [];
  out.push(
    `DORA software delivery metrics (definitions: https://dora.dev/guides/dora-metrics/); deploys = ${report.deploys}` +
      (report.since ? ` since ${report.since.slice(0, 10)}` : ""),
  );
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
  return out;
}
