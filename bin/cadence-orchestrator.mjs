#!/usr/bin/env node
// Vendor the tpm kit into a repository for one or more agent platforms.
//
// Copies core (SKILL.md, references, guard + runtime) and the platform shim into
// the platform's skills directory, and merges hook config idempotently: earlier
// tpm entries are replaced, everything else in the file is kept. Run once per
// repo, then commit the result. No dependencies. The guard itself is stdlib
// Python, so the target machine needs python3 for the hooks to run.

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { MANIFEST, SCRIPTS, hasGuard, installed, readManifest as manifestOf } from "./doctor.mjs";

// No raw stack traces: one line with the cause (the full stack with DEBUG set). A refused write is usually an
// agent's sandbox.
function crashed(e) {
  if (process.env.DEBUG) console.error(e?.stack ?? e);
  const line = String(e?.message ?? e).split("\n")[0];
  if (["EACCES", "EPERM", "EROFS"].includes(e?.code)) {
    console.error(
      `cadence-orchestrator: permission denied (${e.code}) on ${e.path ?? "a file in the repo"}. ` +
        "If an agent ran this, its sandbox may need to allow writes to the repo.",
    );
  } else console.error(`cadence-orchestrator: ${line}`);
  process.exit(1);
}
process.on("uncaughtException", crashed);
process.on("unhandledRejection", crashed);

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CORE = path.join(ROOT, "skills", "tpm"); // the skill, in the Agent Skills layout
const ADAPTERS = path.join(ROOT, "adapters");
const MARK = "skills/tpm/scripts/shim_"; // identifies our hook entries on re-install
const BLOCK = /<!-- cadence-orchestrator:tpm begin -->[\s\S]*?<!-- cadence-orchestrator:tpm end -->\n?/g;

// `detect`: what in a repo shows it uses that editor, for a run without --target.
// `guard: false` marks an instructions-only target: the skill and no hooks. Its `marker` is a file only that target
// writes, so a skill folder shared with other targets never makes it look installed.
const TARGETS = {
  antigravity: {
    // Skills: https://antigravity.google/docs/skills (.agents/skills, run as /<name>).
    // Rules: https://antigravity.google/docs/rules (.agents/rules/*.md need a `trigger` in frontmatter).
    // Hooks: https://antigravity.google/docs/hooks (no hook input carries the prompt, so nothing can arm a guard).
    skill: ".agents/skills/tpm",
    guard: false,
    marker: ".agents/rules/tpm.md",
    files: [["antigravity/tpm.rule.md", ".agents/rules/tpm.md"]],
    detect: [".agent", ".agents/rules", ".agents/workflows", ".agents/hooks.json"],
  },
  claude: {
    skill: ".claude/skills/tpm",
    hooks: [["claude/settings.hooks.json", ".claude/settings.json"]],
    detect: [".claude"],
  },
  codex: {
    skill: ".agents/skills/tpm",
    detect: [".codex"], // not AGENTS.md: other tools read it too
    hooks: [["codex/hooks.json", ".codex/hooks.json"]],
    blocks: [["codex/AGENTS.pointer.md", "AGENTS.md"]],
  },
  copilot: {
    skill: ".github/skills/tpm",
    hooks: [["copilot/hooks.json", ".github/hooks/tpm.json"]],
    detect: [".github/copilot-instructions.md", ".github/hooks"],
  },
  cursor: {
    skill: ".agents/skills/tpm",
    hooks: [["cursor/hooks.json", ".cursor/hooks.json"]],
    files: [["cursor/tpm.mdc", ".cursor/rules/tpm.mdc"]],
    detect: [".cursor"],
  },
  gemini: {
    skill: ".agents/skills/tpm",
    detect: [".gemini"],
    hooks: [["gemini/settings.hooks.json", ".gemini/settings.json"]],
    blocks: [["gemini/GEMINI.pointer.md", "GEMINI.md"]],
  },
};

// For a run without --target in a repo with no editor marker yet: variables an agent documents setting in the
// commands it runs. Antigravity documents none, so it isn't detected this way.
const HOST_ENV = {
  claude: ["CLAUDECODE"], // https://code.claude.com/docs/en/env-vars
  // Published source: https://github.com/openai/codex/blob/main/codex-rs/core/src/exec_env.rs (CODEX_THREAD_ID)
  // and https://github.com/openai/codex/blob/main/codex-rs/core/src/spawn.rs (the two sandbox variables).
  codex: ["CODEX_THREAD_ID", "CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED"],
  cursor: ["CURSOR_AGENT"], // https://cursor.com/docs/agent/terminal
  gemini: ["GEMINI_CLI"], // https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/shell.md
};

const read = (p) => fs.readFileSync(p, "utf8");
const exists = (p) => fs.existsSync(p);
const template = (rel, skill) => read(path.join(ADAPTERS, rel)).replaceAll("__SKILL__", skill);

// Installs and uninstalls are planned first, in memory: `plan` maps a repo-relative path to its new text (null
// deletes it). Every file the run touches is read and checked while planning, so an invalid hook file or a broken
// managed block stops the run before anything is written.
const BEGIN = "<!-- cadence-orchestrator:tpm begin -->";
const END = "<!-- cadence-orchestrator:tpm end -->";
const PKG_VERSION = JSON.parse(read(path.join(ROOT, "package.json"))).version;
const sha = (text) => createHash("sha256").update(text).digest("hex");

function current(plan, rel) {
  if (plan.has(rel)) return plan.get(rel);
  const file = path.join(repo, rel);
  return exists(file) && fs.statSync(file).isFile() ? read(file) : null;
}

function parseJson(rel, text) {
  try {
    return JSON.parse(text);
  } catch (e) {
    fail(`${rel} isn't valid JSON (${e.message}); fix it and run again. Nothing was changed.`);
  }
}

// Remove the managed block, touching only the blank lines right around it.
function removeBlock(text) {
  const start = text.indexOf(BEGIN);
  const end = text.indexOf(END, start) + END.length;
  const before = text.slice(0, start).replace(/\n+$/, "");
  const after = text.slice(end).replace(/^\n+/, "");
  if (!before) return after;
  return after ? `${before}\n\n${after}` : `${before}\n`;
}

function checkMarkers(rel, text) {
  const begins = text.split(BEGIN).length - 1;
  const ends = text.split(END).length - 1;
  if (begins !== ends || (text.match(BLOCK) ?? []).length !== begins) {
    fail(`${rel} has a cadence-orchestrator begin marker without a matching end marker (or the reverse); fix it and run again. Nothing was changed.`);
  }
}

function listFiles(src, rel = "") {
  return fs.readdirSync(path.join(src, rel), { withFileTypes: true }).flatMap((e) => {
    const r = rel ? `${rel}/${e.name}` : e.name;
    return e.isDirectory() ? listFiles(src, r) : [r];
  });
}

// The skill folder's files, relative to the folder: SKILL.md, references/, the shared scripts.
function skillFiles(target) {
  let text = read(path.join(CORE, "SKILL.md"));
  if (target === "claude") {
    // Claude Code only: the user, not the model, starts it (the guard arms on that).
    text = text.replace("\n---\n", "\ndisable-model-invocation: true\n---\n");
  }
  const files = { "SKILL.md": text };
  for (const f of listFiles(path.join(CORE, "references"))) files[`references/${f}`] = read(path.join(CORE, "references", f));
  for (const name of SCRIPTS) files[`scripts/${name}`] = read(path.join(CORE, "scripts", name));
  return files;
}

// Hook files must be an object whose `hooks` is an object of lists; anything else stops the run before writing.
function hookConfig(rel, text) {
  const cur = text === null ? {} : parseJson(rel, text);
  const bad = (why) => fail(`${rel} isn't valid hook config (${why}); fix it and run again. Nothing was changed.`);
  if (!cur || typeof cur !== "object" || Array.isArray(cur)) bad("it should be a JSON object");
  if (cur.hooks !== undefined && (!cur.hooks || typeof cur.hooks !== "object" || Array.isArray(cur.hooks))) bad("hooks should be an object");
  for (const [event, entries] of Object.entries(cur.hooks ?? {})) if (!Array.isArray(entries)) bad(`hooks.${event} should be a list`);
  return cur;
}

function planHooks(plan, rel, ours) {
  const cur = hookConfig(rel, current(plan, rel));
  for (const [key, value] of Object.entries(ours)) {
    if (key !== "hooks" && !(key in cur)) cur[key] = value;
  }
  cur.hooks ??= {};
  for (const [event, entries] of Object.entries(ours.hooks)) {
    const kept = (cur.hooks[event] ?? []).filter((e) => !JSON.stringify(e).includes(MARK));
    cur.hooks[event] = [...kept, ...entries];
  }
  plan.set(rel, JSON.stringify(cur, null, 2) + "\n");
}

function planBlock(plan, rel, block) {
  const text = current(plan, rel) ?? "";
  checkMarkers(rel, text);
  // An existing block is replaced where it is; otherwise the block goes at the end.
  if (text.includes(BEGIN)) plan.set(rel, text.replace(BLOCK, () => block));
  else plan.set(rel, (text.replace(/\n+$/, "") ? text.replace(/\n+$/, "") + "\n\n" : "") + block);
}

const GITIGNORE = ["# tpm off switch (user-local)", ".cadence/tpm.off"];

function planGitignore(plan) {
  // Ignore only the off switch: .cadence/catalog/ is meant to be committed.
  let lines = (current(plan, ".gitignore") ?? "").split("\n");
  lines = lines.map((l) => (l === ".cadence/" ? ".cadence/tpm.off" : l)); // older installs
  if (!lines.includes(".cadence/tpm.off")) {
    while (lines.length && lines.at(-1) === "") lines.pop();
    lines.push(...GITIGNORE);
  }
  plan.set(".gitignore", lines.join("\n").replace(/^\n+/, "").replace(/\n+$/, "") + "\n");
}

// Per target: its shim and its own files. Skill folders are planned separately, once each.
function planTarget(plan, target) {
  const spec = TARGETS[target];
  const touched = [spec.skill + "/"];
  if (hasGuard(spec)) plan.set(`${spec.skill}/scripts/shim_${target}.py`, read(path.join(ADAPTERS, target, "shim.py")));
  for (const [src, dst] of spec.hooks ?? []) {
    planHooks(plan, dst, JSON.parse(template(src, spec.skill)));
    touched.push(dst);
  }
  for (const [src, dst] of spec.files ?? []) {
    plan.set(dst, template(src, spec.skill));
    touched.push(dst);
  }
  for (const [src, dst] of spec.blocks ?? []) {
    planBlock(plan, dst, template(src, spec.skill));
    touched.push(dst);
  }
  return touched;
}

const stale = []; // files earlier versions installed that this one doesn't

function planSkill(plan, target, skill, targets) {
  const files = skillFiles(target);
  for (const [rel, text] of Object.entries(files)) plan.set(`${skill}/${rel}`, text);
  for (const t of targets.filter((t) => TARGETS[t].skill === skill && hasGuard(TARGETS[t]))) {
    files[`scripts/shim_${t}.py`] = read(path.join(ADAPTERS, t, "shim.py"));
  }
  const hashes = Object.fromEntries(Object.entries(files).sort().map(([rel, text]) => [rel, sha(text)]));
  const old = readManifest(skill);
  for (const [rel, h] of Object.entries(old?.files ?? {})) {
    if (rel in hashes) continue;
    // Shims other targets installed into this shared folder earlier stay, with their hashes.
    if (rel.startsWith("scripts/shim_") && exists(path.join(repo, skill, rel))) hashes[rel] = h;
    // A file an older version installed and this one doesn't: removed (backed up first if edited), so the
    // manifest always matches what's on disk.
    else if (!rel.startsWith("scripts/shim_")) {
      plan.set(`${skill}/${rel}`, null);
      stale.push(`${skill}/${rel}`);
    }
  }
  plan.set(`${skill}/${MANIFEST}`, JSON.stringify({ version: PKG_VERSION, files: sortKeys(hashes) }, null, 2) + "\n");
}

const sortKeys = (o) => Object.fromEntries(Object.entries(o).sort(([a], [b]) => (a < b ? -1 : 1)));

const readManifest = (skill) => manifestOf(repo, skill);
const skillOf = (rel) => Object.values(TARGETS).map((s) => s.skill).find((s) => rel.startsWith(s + "/"));
const STAMP = new Date().toISOString().replace(/[-:]/g, "").replace(/\..*/, "Z"); // one backup folder per run

// JSON files compare by value, so a reformatted but equal file isn't a change.
function same(rel, a, b) {
  if (a === b) return true;
  if (a === null || b === null || !rel.endsWith(".json")) return false;
  try {
    return JSON.stringify(JSON.parse(a)) === JSON.stringify(JSON.parse(b));
  } catch {
    return false;
  }
}

function changes(plan) {
  const out = [];
  for (const [rel, text] of plan) {
    const file = path.join(repo, rel);
    const disk = exists(file) && fs.statSync(file).isFile() ? read(file) : null;
    if (!same(rel, disk, text)) out.push({ rel, text, action: text === null ? "remove" : disk === null ? "create" : "update" });
  }
  return out.sort((a, b) => (a.rel < b.rel ? -1 : 1));
}

// Write the plan. Every manifest is read before the first write or delete, and the new manifests are written last,
// so each file is compared with the hash recorded when it was installed. A skill file that no longer matches that
// hash was edited by hand: it is copied to .cadence/backups/<run time>/ before it is overwritten or deleted.
// Installs from before manifests existed have no hashes, so nothing of theirs is backed up.
function apply(plan) {
  const manifests = new Map(Object.values(TARGETS).map((s) => [s.skill, readManifest(s.skill)]));
  const all = changes(plan);
  const isManifest = (rel) => rel.endsWith("/" + MANIFEST);
  const backups = [];
  for (const { rel, text } of [...all.filter((c) => !isManifest(c.rel)), ...all.filter((c) => isManifest(c.rel))]) {
    const file = path.join(repo, rel);
    const skill = skillOf(rel);
    const recorded = skill && !isManifest(rel) && manifests.get(skill)?.files?.[rel.slice(skill.length + 1)];
    if (recorded && exists(file) && recorded !== sha(read(file))) {
      const dest = path.join(repo, ".cadence", "backups", STAMP, rel);
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      fs.copyFileSync(file, dest);
      backups.push({ rel, to: path.relative(repo, dest), removed: text === null });
    }
    if (text === null) fs.rmSync(file, { force: true });
    else {
      fs.mkdirSync(path.dirname(file), { recursive: true });
      fs.writeFileSync(file, text);
    }
  }
  return backups;
}

function addCatalogs(plan, files) {
  return files.map((f) => {
    if (!f.endsWith(".md")) fail(`catalog ${f} must be a .md file`);
    const rel = ".cadence/catalog/" + path.basename(f);
    plan.set(rel, read(f));
    return rel;
  });
}

// Uninstall: only what the installer adds. Hook entries carrying our marker, our managed block, our files, our
// shim, the skill folder once no remaining target uses it, and the .gitignore lines once nothing is left.
// Bytecode compiled from tpm's own scripts, in tpm's own skill folder: <stem>.*.pyc for each script the manifest lists
// (or this version's scripts for an older install). Other files there, and every other skill's folders, are left
// alone; __pycache__ itself goes only if that leaves it empty.
function cleanPycache(skill, manifest) {
  const dir = path.join(repo, skill, "scripts", "__pycache__");
  if (!exists(dir)) return;
  const scripts = manifest?.files
    ? Object.keys(manifest.files).filter((f) => /^scripts\/[^/]+\.py$/.test(f))
    : [...SCRIPTS.map((n) => `scripts/${n}`), ...Object.keys(TARGETS).map((t) => `scripts/shim_${t}.py`)];
  const stems = new Set(scripts.map((f) => path.basename(f, ".py")));
  // PEP 488 names: <stem>.<tag>.pyc, and <stem>.<tag>.opt-<level>.pyc for -O/-OO (https://peps.python.org/pep-0488/).
  const bytecode = /^\.[^.]+(\.opt-[0-9]+)?\.pyc$/;
  for (const name of fs.readdirSync(dir)) {
    const stem = [...stems].find((st) => name.startsWith(st + ".") && bytecode.test(name.slice(st.length)));
    if (stem) fs.rmSync(path.join(dir, name), { force: true });
  }
  try {
    if (!fs.readdirSync(dir).length) fs.rmdirSync(dir);
  } catch {}
}

const pycache = []; // [skill folder, manifest] pairs whose tpm bytecode uninstall cleans

function planUninstall(plan, targets, remaining) {
  const removed = [];
  for (const t of targets) {
    const spec = TARGETS[t];
    for (const [src, dst] of spec.hooks ?? []) {
      const text = current(plan, dst);
      if (text === null) continue;
      const cur = hookConfig(dst, text);
      const ours = JSON.parse(template(src, spec.skill));
      let hit = false;
      for (const event of Object.keys(cur.hooks ?? {})) {
        const kept = (cur.hooks[event] ?? []).filter((e) => !JSON.stringify(e).includes(MARK));
        if (kept.length !== cur.hooks[event].length) hit = true;
        if (kept.length) cur.hooks[event] = kept;
        else delete cur.hooks[event];
      }
      if (!hit) continue;
      if (cur.hooks && !Object.keys(cur.hooks).length) delete cur.hooks;
      // Keys we added only when missing (like Cursor's "version") go too if nothing else is left.
      const left = Object.entries(cur).filter(([k, v]) => !(k in ours && JSON.stringify(v) === JSON.stringify(ours[k])));
      plan.set(dst, left.length ? JSON.stringify(cur, null, 2) + "\n" : null);
      removed.push(`${dst} (hook entries)`);
    }
    for (const [, dst] of spec.blocks ?? []) {
      const text = current(plan, dst);
      if (text === null || !text.includes(BEGIN)) continue;
      checkMarkers(dst, text);
      plan.set(dst, removeBlock(text) || null);
      removed.push(`${dst} (tpm block)`);
    }
    for (const [, dst] of spec.files ?? []) {
      if (current(plan, dst) === null) continue;
      plan.set(dst, null);
      removed.push(dst);
    }
    const shim = `${spec.skill}/scripts/shim_${t}.py`;
    if (hasGuard(spec) && current(plan, shim) !== null) {
      plan.set(shim, null);
      removed.push(shim);
    }
  }
  for (const skill of new Set(targets.map((t) => TARGETS[t].skill))) {
    const manifest = readManifest(skill);
    if (remaining.some((t) => TARGETS[t].skill === skill)) {
      // The folder stays for another target: drop the uninstalled shims from its record.
      if (manifest) {
        const files = { ...manifest.files };
        for (const t of targets) delete files[`scripts/shim_${t}.py`];
        plan.set(`${skill}/${MANIFEST}`, JSON.stringify({ ...manifest, files }, null, 2) + "\n");
      }
      continue;
    }
    if (current(plan, `${skill}/SKILL.md`) === null && !manifest) continue;
    // What the manifest records was installed; for an install from before manifests, this version's file list.
    const owner = targets.find((t) => TARGETS[t].skill === skill);
    const ours = [...Object.keys(manifest?.files ?? skillFiles(owner)), "SKILL.md", MANIFEST];
    for (const rel of ours) if (current(plan, `${skill}/${rel}`) !== null) plan.set(`${skill}/${rel}`, null);
    pycache.push([skill, manifest]);
    removed.push(`${skill}/ (${manifest ? "the files its install manifest records" : "this version's skill files"})`);
  }
  if (!remaining.length) {
    const text = current(plan, ".gitignore");
    if (text !== null && text.split("\n").includes(".cadence/tpm.off")) {
      const rest = text.split("\n").filter((l) => !GITIGNORE.includes(l)).join("\n").replace(/\n+$/, "");
      plan.set(".gitignore", rest ? rest + "\n" : null);
      removed.push(".gitignore (tpm off-switch lines)");
    }
  }
  return removed;
}

// Folders this run will create: the parents of planned files that don't exist yet. They are recorded in each
// install manifest (with the ones earlier installs recorded), so uninstall removes only folders the installer made.
function recordCreatedDirs(plan) {
  const created = new Set();
  for (const [rel, text] of plan) {
    if (text === null) continue;
    for (let dir = path.dirname(rel); dir !== "." && !exists(path.join(repo, dir)); dir = path.dirname(dir)) created.add(dir);
  }
  for (const [rel, text] of plan) {
    if (text === null || !rel.endsWith("/" + MANIFEST)) continue;
    const old = readManifest(rel.slice(0, -MANIFEST.length - 1));
    const dirs = [...new Set([...(old?.created_dirs ?? []), ...created])].sort();
    plan.set(rel, JSON.stringify({ ...JSON.parse(text), created_dirs: dirs }, null, 2) + "\n");
  }
}

// What earlier installs recorded as created, read before uninstall deletes the manifests. Installs from before
// manifests recorded it give nothing, so their folders are kept.
const createdDirs = () => Object.values(TARGETS).flatMap((s) => readManifest(s.skill)?.created_dirs ?? []);

// A file's parent folders inside the repo, deepest first.
function parentsWithin(rel) {
  const out = [];
  for (let dir = path.dirname(rel); dir !== "."; dir = path.dirname(dir)) out.push(dir);
  return out;
}

// Remove a folder only if the installer created it and it's now empty, and never a skills or hooks folder (other
// tools keep theirs there).
function pruneCreated(dirs) {
  const removed = [];
  for (const dir of [...new Set(dirs)].sort((a, b) => b.split("/").length - a.split("/").length || (a < b ? 1 : -1))) {
    if (["skills", "hooks"].includes(path.basename(dir))) continue;
    const abs = path.join(repo, dir);
    try {
      if (fs.readdirSync(abs).length) continue;
      fs.rmdirSync(abs);
      removed.push(dir + "/");
    } catch {}
  }
  return removed;
}

function fail(message, code = 1) {
  console.error(`cadence-orchestrator: ${message}`);
  process.exit(code);
}

const NAMES = Object.keys(TARGETS).sort().join("|");
const USAGE = `usage: cadence-orchestrator [--target <${NAMES}|all>] [--repo <path>] [--catalog <file.md>]... [--dry-run|--check]
       cadence-orchestrator uninstall [--target <...|all>] [--repo <path>] [--dry-run]
       cadence-orchestrator doctor --target <...|all> [--repo <path>] [--json]
       cadence-orchestrator status [--repo <path>] [--hours <n>] [--state-dir <path>] [--json]
       cadence-orchestrator dora [--repo <path>] [--since <date>] [--deploys tags|merges|npm] [--include-prereleases] [--json]

Vendors the tpm skill and its guard hooks into the git repository you're in (or the one at --repo), for --target
or, without it, every editor the repo has config for (or else the agent running it). Re-running is safe.
\`--dry-run\` prints what would change and writes nothing; \`--check\` exits 1 if the installed files differ from what
this version would write. \`uninstall\` removes only what the installer added (default: every installed target).
\`doctor\` checks an installed target (files, hook config, python3, simulated hook events) and changes nothing.
\`dora\` computes DORA's delivery metrics from git (read-only).
\`status\` reports what's installed and whether hooks have been seen firing in a live session (default: last 24 h).`;

function parseArgs(argv, mode) {
  const opts = { repo: null, catalog: [], hours: 24, stateDir: "", since: null, deploys: "tags", json: false };
  for (let i = 0; i < argv.length; i++) {
    const [flag, inline] = argv[i].split(/=(.*)/s, 2);
    const value = () => inline ?? argv[++i] ?? fail(`${flag} needs a value\n${USAGE}`, 2);
    if (flag === "--target") opts.target = value();
    else if (flag === "--repo") {
      // A bare --repo (last, or followed by a --flag, known or not) means "here", like no --repo at all.
      const next = argv[i + 1];
      const bare = inline === undefined && (next === undefined || next.startsWith("--"));
      opts.repo = bare ? null : inline === undefined ? argv[++i] : inline || null;
    }
    else if (flag === "--catalog" && mode === "install") opts.catalog.push(value());
    else if (flag === "--state-dir" && mode === "status") opts.stateDir = value();
    else if (flag === "--since" && mode === "dora") {
      opts.since = new Date(value());
      if (Number.isNaN(opts.since.getTime())) fail(`--since needs a date like 2026-01-31\n${USAGE}`, 2);
    } else if (flag === "--deploys" && mode === "dora") {
      opts.deploys = value();
      if (!["tags", "merges", "npm"].includes(opts.deploys)) fail(`--deploys is tags, merges or npm\n${USAGE}`, 2);
    } else if (flag === "--json" && ["dora", "status", "doctor"].includes(mode)) opts.json = true;
    else if (flag === "--dry-run" && ["install", "uninstall"].includes(mode)) opts.dryRun = true;
    else if (flag === "--check" && mode === "install") opts.check = true;
    else if (flag === "--include-prereleases" && mode === "dora") opts.includePrereleases = true;
    else if (flag === "--hours" && mode === "status") {
      opts.hours = Number(value());
      if (!(opts.hours > 0)) fail(`--hours needs a positive number\n${USAGE}`, 2);
    }
    else if (flag === "-h" || flag === "--help") {
      console.log(USAGE);
      process.exit(0);
    } else if (["--catalog", "--hours", "--target", "--state-dir", "--since", "--deploys", "--json", "--include-prereleases", "--dry-run", "--check"].includes(flag)) {
      fail(`${mode} doesn't take ${flag}\n${USAGE}`, 2);
    } else fail(`unknown argument ${argv[i]}\n${USAGE}`, 2);
  }
  if (mode === "status" || mode === "dora") {
    if (opts.target) fail(`${mode} doesn't take --target\n${USAGE}`, 2);
    return opts;
  }
  if (opts.dryRun && opts.check) fail(`--dry-run and --check don't go together\n${USAGE}`, 2);
  if (!opts.target && mode === "doctor") fail(`--target is required\n${USAGE}`, 2);
  if (opts.target && opts.target !== "all" && !(opts.target in TARGETS)) fail(`unknown target ${opts.target}\n${USAGE}`, 2);
  return opts;
}

const argv = process.argv.slice(2);
const mode = ["doctor", "status", "dora", "uninstall"].includes(argv[0]) ? argv[0] : "install";
const isDoctor = mode === "doctor";
const opts = parseArgs(mode === "install" ? argv : argv.slice(1), mode);
// --repo <path> must be a repository root. Without it, the repository containing the current folder (the nearest
// folder up with a .git); when installing, that walk-up never lands on the home directory (a dotfiles repo).
function findRepo(explicit) {
  const real = (p) => (exists(p) ? fs.realpathSync(p) : p);
  const home = real(os.homedir());
  if (explicit) {
    const repo = path.resolve(explicit);
    if (!exists(path.join(repo, ".git"))) fail(`${repo} is not a git repository root`);
    return repo;
  }
  for (let dir = process.cwd(); ; dir = path.dirname(dir)) {
    if (exists(path.join(dir, ".git"))) {
      if (["install", "uninstall"].includes(mode) && real(dir) === home) {
        fail(`${dir} is your home directory; run this inside a project's repository, or pass --repo`);
      }
      return dir;
    }
    if (path.dirname(dir) === dir) fail(`${process.cwd()} is not inside a git repository`);
  }
}
const repo = findRepo(opts.repo);
if (mode === "dora") {
  const { dora, formatDora } = await import("./dora.mjs");
  const report = dora(repo, { since: opts.since, deploys: opts.deploys, includePrereleases: opts.includePrereleases });
  console.log(opts.json ? JSON.stringify(report, null, 2) : formatDora(report).join("\n"));
  process.exit(0);
}
if (mode === "status") {
  const { status } = await import("./status.mjs");
  const { lines, ok, data } = status(repo, TARGETS, opts.hours, opts.stateDir, PKG_VERSION);
  if (opts.json) console.log(JSON.stringify({ ok, repo, version: PKG_VERSION, ...data, lines }, null, 2));
  else for (const l of lines) console.log(l);
  process.exit(ok ? 0 : 1);
}
if (isDoctor) {
  const { doctor, guiPathNote } = await import("./doctor.mjs");
  let targets = [opts.target];
  const results = [];
  if (opts.target === "all") {
    const found = Object.keys(TARGETS)
      .sort()
      .map((t) => ({ t, ...installed(repo, t, TARGETS[t]) }));
    for (const f of found.filter((f) => f.error)) results.push({ name: `${f.t}: ${f.error}`, ok: false });
    for (const f of found.filter((f) => !f.installed && !f.error)) {
      results.push({ name: `${f.t}: not installed`, ok: true, skip: true });
    }
    targets = found.filter((f) => f.installed).map((f) => f.t);
    if (!targets.length && !results.some((r) => !r.ok)) {
      results.push({ name: `no target is installed in ${repo}`, ok: false });
    }
  }
  results.push(...targets.flatMap((t) => doctor(repo, t, TARGETS[t])));
  const note = targets.some((t) => hasGuard(TARGETS[t])) ? guiPathNote() : ""; // once per run, not per target
  if (note) results.push({ name: `note: ${note}`, ok: true, skip: true });
  const failed = results.filter((r) => !r.ok).length;
  const ran = results.filter((r) => !r.skip).length;
  if (opts.json) {
    const checks = results.map(({ name, ok, skip, detail }) => ({ name, ok, skip: !!skip, detail: detail || "" }));
    console.log(JSON.stringify({ ok: !failed, repo, failed, ran, checks }, null, 2));
    process.exit(failed ? 1 : 0);
  }
  for (const r of results) {
    const mark = r.skip ? "skip" : r.ok ? "ok  " : "FAIL";
    console.log(`${mark} ${r.name}${r.ok || !r.detail ? "" : `: ${r.detail}`}`);
  }
  console.log(failed ? `${failed} check(s) failed.` : `All ${ran} checks passed.`);
  if (!failed && targets.some((t) => hasGuard(TARGETS[t]))) {
    console.log(
      "Simulation passed; this does not confirm the hooks fire in a live session. Run " +
        "`npx cadence-orchestrator status` after starting a session here with $tpm (Codex) or /tpm.",
    );
  }
  process.exit(failed ? 1 : 0);
}
// Without --target: the editors the repo has config for; failing that, the agent this runs under.
function detect() {
  const names = Object.keys(TARGETS).sort();
  const found = names.filter((t) => TARGETS[t].detect.some((m) => exists(path.join(repo, m))));
  if (found.length) return { targets: found, how: "detected" };
  const vars = names.flatMap((t) => (HOST_ENV[t] ?? []).filter((v) => process.env[v]).slice(0, 1).map((v) => [t, v]));
  if (vars.length) return { targets: vars.map(([t]) => t), how: `running under it: ${vars.map(([, v]) => v).join(", ")}` };
  fail(`no editor config found in ${repo} and no supported agent detected; choose one with --target <${NAMES}|all>`, 2);
}
const installedNow = () => Object.keys(TARGETS).sort().filter((t) => installed(repo, t, TARGETS[t]).installed);
const all = Object.keys(TARGETS).sort();

if (mode === "uninstall") {
  const before = installedNow();
  const targets = opts.target ? (opts.target === "all" ? all : [opts.target]) : before;
  const remaining = before.filter((t) => !targets.includes(t));
  const plan = new Map();
  const removed = planUninstall(plan, targets, remaining);
  if (!removed.length) {
    console.log(`Nothing to remove in ${repo}${opts.target ? ` for ${targets.join(", ")}` : ""}.`);
    process.exit(0);
  }
  console.log(`${opts.dryRun ? "Would remove" : "Removing"} from ${repo}:`);
  for (const r of removed) console.log(`  ${r}`);
  if (opts.dryRun) {
    console.log("Dry run: nothing was changed.");
    process.exit(0);
  }
  const dirs = createdDirs();
  const backups = apply(plan);
  for (const [skill, m] of pycache) cleanPycache(skill, m);
  for (const b of backups) console.log(`backed up hand-edited ${b.rel} to ${b.to} before removing it`);
  const pruned = pruneCreated(dirs);
  if (pruned.length) console.log(`Removed empty folders it had created: ${pruned.join(", ")}`);
  console.log("Done. Review and commit the changes.");
  process.exit(0);
}

let chosen;
if (opts.check && !opts.target) {
  chosen = { targets: installedNow() };
  if (!chosen.targets.length) fail(`no target is installed in ${repo}; nothing to check`);
} else chosen = opts.target ? { targets: opts.target === "all" ? all : [opts.target] } : detect();
const targets = chosen.targets;
const guarded = targets.filter((t) => hasGuard(TARGETS[t]));

// Plan everything first: invalid JSON or a broken block stops here, before any write.
const plan = new Map();
const folders = new Map(targets.map((t) => [TARGETS[t].skill, t])); // shared folders (.agents/skills/tpm) once
for (const [skill, t] of folders) planSkill(plan, t, skill, targets);
const touched = targets.map((t) => planTarget(plan, t));
planGitignore(plan);
const catalogs = addCatalogs(plan, opts.catalog);
recordCreatedDirs(plan);
const diff = changes(plan);

if (opts.check || opts.dryRun) {
  const verb = opts.check ? "differs" : "would";
  for (const c of diff) console.log(opts.check ? `${verb}: ${c.rel}` : `${verb} ${c.action} ${c.rel}`);
  if (opts.check) {
    console.log(diff.length ? `${diff.length} file(s) differ from what ${PKG_VERSION} would write; reinstall to update.` : `Up to date with ${PKG_VERSION} for ${targets.join(", ")}.`);
    process.exit(diff.length ? 1 : 0);
  }
  console.log(`Dry run for ${targets.join(", ")} in ${repo}: ${diff.length} file(s) would change; nothing was written.`);
  process.exit(0);
}

console.log(`Installing into ${repo}${chosen.how ? ` for ${targets.join(", ")} (${chosen.how})` : ""}`);
const py = guarded.length ? spawnSync("python3", ["--version"], { stdio: "ignore" }) : { status: 0 };
if (py.error || py.status !== 0) {
  console.error("warning: python3 is not on PATH. The guard hooks run python3 and will not work until it is installed.");
}
// 0.1.0 hooks left bytecode caches next to the vendored scripts; remove them (only inside the skill dir).
const oldManifests = new Map([...folders.keys()].map((skill) => [skill, readManifest(skill)]));
const dirs = createdDirs();
const backups = apply(plan);
for (const [skill, m] of oldManifests) cleanPycache(skill, m ?? null);
for (const rel of stale) console.log(`removed ${rel} (no longer part of tpm ${PKG_VERSION})`);
pruneCreated(stale.flatMap((rel) => parentsWithin(rel)).filter((d) => dirs.includes(d)));
targets.forEach((t, k) => {
  console.log(`${t}: ${touched[k].join(", ")}${hasGuard(TARGETS[t]) ? "" : " (instructions only, no guard)"}`);
});
if (catalogs.length) console.log(`catalog: ${catalogs.join(", ")}`);
for (const b of backups) console.log(`backed up hand-edited ${b.rel} to ${b.to}${b.removed ? " before removing it" : ""}`);
console.log("Done. Review and commit the changes; see README for per-platform notes.");
if (guarded.length) console.log("Reload once: start a new chat or session in this repo, so the hooks load (approve them if asked).");
for (const t of targets) {
  // Codex has no project slash commands; it mentions skills with $ (https://learn.chatgpt.com/docs/build-skills).
  console.log(`${t}: start with ${t === "codex" ? "$tpm" : "/tpm"}${hasGuard(TARGETS[t]) ? "" : " (instructions only)"}`);
}
if (guarded.length) console.log("Then check the guard is running: npx cadence-orchestrator status");
