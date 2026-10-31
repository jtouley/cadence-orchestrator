// `cadence-orchestrator status`: is the guard actually running here? Reports separately what's installed
// and what has been seen firing. Hooks write a heartbeat (<state>/sessions/<session>.json) on every event;
// only those prove the guard runs in a live session. Reads only; changes nothing.

import fs from "node:fs";
import path from "node:path";
import { hookEntries, installed, resolveStateDir } from "./doctor.mjs";

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

export function status(repo, TARGETS, hours, stateDir = "") {
  const lines = [];
  let anyInstalled = false;
  let anyLive = false;
  const states = new Map();
  for (const target of Object.keys(TARGETS).sort()) {
    const spec = TARGETS[target];
    const inst = installed(repo, target, spec);
    const skillFiles = ["SKILL.md", `scripts/shim_${target}.py`].every((f) => fs.existsSync(path.join(repo, spec.skill, f)));
    if (!inst.installed && !skillFiles) {
      lines.push(`${target}: not installed`);
      continue;
    }
    anyInstalled = true;
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
  if (!anyInstalled) lines.push("No target is installed in this repo.");
  else if (!anyLive) {
    lines.push(
      "No live hook activity: the files are installed, but the guard hasn't been seen running. Start a new session " +
        "in this repo, approve its hooks if asked, start with /tpm ($tpm on Codex), then run status again from inside " +
        "that session (so it sees the agent's environment), or pass --state-dir.",
    );
  }
  return { lines, ok: anyLive };
}
