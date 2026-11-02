// `cadence-orchestrator status`: is the guard actually running here? Reports separately what's installed
// and what has been seen firing. Hooks write a heartbeat (<state>/sessions/<session>.json) on every event;
// only those prove the guard runs in a live session. Reads only; changes nothing.

import fs from "node:fs";
import path from "node:path";
import { hasGuard, hookEntries, installed, resolveStateDir } from "./doctor.mjs";

const ago = (seconds) =>
  seconds < 90 ? `${Math.round(seconds)} s ago` : seconds < 5400 ? `${Math.round(seconds / 60)} min ago` : `${(seconds / 3600).toFixed(1)} h ago`;

function sessions(stateDir, repo, hours) {
  const dir = path.join(stateDir, "sessions");
  const now = Date.now() / 1000;
  const real = fs.realpathSync(repo);
  const out = [];
  let names = [];
  try {
    names = fs.readdirSync(dir).filter((n) => n.endsWith(".json"));
  } catch {
    return out;
  }
  for (const name of names) {
    try {
      const s = JSON.parse(fs.readFileSync(path.join(dir, name), "utf8"));
      // Heartbeats record the git top level, so an exact match counts subdirectories but not nested repos.
      if (s.project === real && now - s.time <= hours * 3600) out.push({ ...s, age: now - s.time });
    } catch {}
  }
  return out.sort((a, b) => a.age - b.age);
}

// A guarded target's own files, other than its hook config and shim: files it writes, its pointer block, and its
// skill folder when no other target shares it.
function leftovers(repo, spec, TARGETS) {
  const found = (spec.files ?? []).map(([, dst]) => dst).filter((f) => fs.existsSync(path.join(repo, f)));
  for (const [, dst] of spec.blocks ?? []) {
    try {
      if (fs.readFileSync(path.join(repo, dst), "utf8").includes("<!-- cadence-orchestrator:tpm begin -->")) found.push(dst);
    } catch {}
  }
  const shared = Object.values(TARGETS).filter((s) => s.skill === spec.skill).length > 1;
  if (!shared && fs.existsSync(path.join(repo, spec.skill, "SKILL.md"))) found.push(`${spec.skill}/`);
  return found;
}

export function status(repo, TARGETS, hours, stateDir = "") {
  const lines = [];
  let anyInstalled = false;
  let anyLive = false;
  let anyHooked = false;
  let broken = false;
  const reinstall = (t) => `reinstall with \`npx cadence-orchestrator --target ${t}\``;
  const owned = new Set(); // skill folders an installed target accounts for
  const states = new Map();
  for (const target of Object.keys(TARGETS).sort()) {
    const spec = TARGETS[target];
    const inst = installed(repo, target, spec);
    // Installed is per target: a guarded target's shim or hook entries, an instructions-only target's marker.
    if (!inst.installed) {
      // Hook config and shim gone, but the target's own files left behind: its guard is broken, whatever else is
      // installed (an instructions-only target sharing the skill folder must not hide it).
      const left = hasGuard(spec) ? leftovers(repo, spec, TARGETS) : [];
      if (left.length) {
        broken = true;
        lines.push(`${target}: hook config and shim missing (found ${left.join(", ")}); ${reinstall(target)}`);
      } else lines.push(`${target}: not installed`);
      continue;
    }
    anyInstalled = true;
    owned.add(spec.skill);
    if (!hasGuard(spec)) {
      const skill = fs.existsSync(path.join(repo, spec.skill, "SKILL.md"));
      lines.push(`${target}: instructions only, no guard hooks on this platform; skill ${skill ? "found" : "missing"} (${spec.skill})`);
      if (!skill) {
        broken = true;
        lines.push(`${target}: ${reinstall(target)}`);
      }
      continue;
    }
    anyHooked = true;
    const skillFiles = ["SKILL.md", `scripts/shim_${target}.py`].every((f) => fs.existsSync(path.join(repo, spec.skill, f)));
    lines.push(`${target}: skill files ${skillFiles ? "found" : "missing"} (${spec.skill})`);
    const hooks = hookEntries(repo, target, spec);
    const have = hooks.events.filter((e) => e.installed).map((e) => e.event);
    const missing = hooks.events.filter((e) => !e.installed).map((e) => e.event);
    lines.push(
      `${target}: hook config ${missing.length ? "incomplete" : "installed"} in ${hooks.file}` +
        (have.length ? ` (${have.join(", ")})` : "") +
        (missing.length ? `; missing ${missing.join(", ")}` : "") +
        (hooks.error ? `; can't read it (${hooks.error})` : ""),
    );
    if (!skillFiles || missing.length || hooks.error) {
      broken = true;
      lines.push(`${target}: incomplete install; ${reinstall(target)}`);
    }
    const resolved = stateDir
      ? { dir: path.resolve(stateDir), error: "", source: "--state-dir" }
      : resolveStateDir(repo, target, spec);
    const { dir, error, source } = resolved;
    if (!dir) {
      lines.push(`${target}: hooks seen firing: unknown (${error})`);
      continue;
    }
    if (!states.has(dir)) states.set(dir, source);
    const seen = sessions(dir, repo, hours).filter((s) => s.platform === target);
    if (seen.length) {
      anyLive = true;
      const armed = seen.filter((s) => s.armed && !s.switched_off).length;
      const off = seen.filter((s) => s.switched_off).length;
      lines.push(
        `${target}: hooks seen firing: ${seen.length} session(s) in the last ${hours} h, ${armed} armed` +
          (off ? `, ${off} switched off` : ""),
      );
      for (const s of seen.slice(0, 5)) {
        const state = s.switched_off ? "switched off (.cadence/tpm.off)" : s.armed ? "armed" : "not armed";
        lines.push(`  session ${s.session}: ${state}, last ${s.last_event} ${ago(s.age)}`);
      }
    } else {
      lines.push(`${target}: hooks seen firing: none in the last ${hours} h (not running in a live session here yet)`);
    }
  }
  for (const [dir, source] of states) {
    lines.push(`state dir: ${dir} (from ${source})`);
    lines.push(`advisory log: ${path.join(dir, "advisory.log")}`);
  }
  for (const skill of new Set(Object.values(TARGETS).map((s) => s.skill))) {
    if (!owned.has(skill) && fs.existsSync(path.join(repo, skill, "SKILL.md"))) {
      lines.push(`note: ${skill}/ has a tpm skill, but no target here is installed with it`);
    }
  }
  if (!anyInstalled) lines.push("No target is installed in this repo.");
  else if (anyHooked && !anyLive) {
    lines.push(
      "No live hook activity: the files are installed, but the guard hasn't been seen running. Start a new session " +
        "in this repo, approve its hooks if asked, start with /tpm ($tpm on Codex), then run status again from inside " +
        "that session (so it sees the agent's environment), or pass --state-dir.",
    );
  }
  return { lines, ok: !broken && (anyLive || (anyInstalled && !anyHooked)) };
}
