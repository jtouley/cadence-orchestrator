#!/usr/bin/env node
// Vendor the tpm kit into a repository for one or more agent platforms.
//
// Copies core (SKILL.md, references, guard + runtime) and the platform shim into
// the platform's skills directory, and merges hook config idempotently: earlier
// tpm entries are replaced, everything else in the file is kept. Run once per
// repo, then commit the result. No dependencies. The guard itself is stdlib
// Python, so the target machine needs python3 for the hooks to run.

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { hasGuard } from "./doctor.mjs";

// No raw stack traces: one line with the cause. A refused write is usually an agent's sandbox.
function crashed(e) {
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

function write(p, text) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, text);
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const from = path.join(src, entry.name);
    const to = path.join(dest, entry.name);
    entry.isDirectory() ? copyDir(from, to) : fs.copyFileSync(from, to);
  }
}

// Once per skill folder per run: Antigravity, Codex, Cursor and Gemini share .agents/skills/tpm.
function copySkill(repo, target, skill) {
  const dest = path.join(repo, skill);
  let text = read(path.join(CORE, "SKILL.md"));
  if (target === "claude") {
    // Claude Code only: the user, not the model, starts it (the guard arms on that).
    text = text.replace("\n---\n", "\ndisable-model-invocation: true\n---\n");
  }
  write(path.join(dest, "SKILL.md"), text);
  copyDir(path.join(CORE, "references"), path.join(dest, "references"));
  // 0.1.0 hooks left bytecode caches next to the vendored scripts; remove them (only inside the skill dir).
  fs.rmSync(path.join(dest, "scripts", "__pycache__"), { recursive: true, force: true });
  fs.mkdirSync(path.join(dest, "scripts"), { recursive: true });
  for (const name of ["guard.py", "runtime.py", "tasks_check.py"]) {
    fs.copyFileSync(path.join(CORE, "scripts", name), path.join(dest, "scripts", name));
  }
}

function mergeHooks(file, ours) {
  const current = exists(file) ? JSON.parse(read(file)) : {};
  for (const [key, value] of Object.entries(ours)) {
    if (key !== "hooks" && !(key in current)) current[key] = value;
  }
  current.hooks ??= {};
  for (const [event, entries] of Object.entries(ours.hooks)) {
    const kept = (current.hooks[event] ?? []).filter((e) => !JSON.stringify(e).includes(MARK));
    current.hooks[event] = [...kept, ...entries];
  }
  write(file, JSON.stringify(current, null, 2) + "\n");
}

function addBlock(file, block) {
  const text = (exists(file) ? read(file) : "").replace(BLOCK, "").replace(/\n+$/, "");
  write(file, (text ? text + "\n\n" : "") + block);
}

function addGitignore(repo) {
  // Ignore only the off switch: .cadence/catalog/ is meant to be committed.
  const file = path.join(repo, ".gitignore");
  let lines = exists(file) ? read(file).split("\n") : [];
  lines = lines.map((l) => (l === ".cadence/" ? ".cadence/tpm.off" : l)); // older installs
  if (!lines.includes(".cadence/tpm.off")) {
    while (lines.length && lines.at(-1) === "") lines.pop();
    lines.push("# tpm off switch (user-local)", ".cadence/tpm.off");
  }
  write(file, lines.join("\n").replace(/\n+$/, "") + "\n");
}

function addCatalogs(repo, files) {
  const dest = path.join(repo, ".cadence", "catalog");
  fs.mkdirSync(dest, { recursive: true });
  return files.map((f) => {
    if (!f.endsWith(".md")) fail(`catalog ${f} must be a .md file`);
    fs.copyFileSync(f, path.join(dest, path.basename(f)));
    return ".cadence/catalog/" + path.basename(f);
  });
}

function install(repo, target, copied) {
  const spec = TARGETS[target];
  if (!copied.has(spec.skill)) copySkill(repo, target, spec.skill);
  copied.add(spec.skill);
  if (hasGuard(spec)) {
    fs.copyFileSync(path.join(ADAPTERS, target, "shim.py"), path.join(repo, spec.skill, "scripts", `shim_${target}.py`));
  }
  const touched = [spec.skill + "/"];
  for (const [src, dst] of spec.hooks ?? []) {
    mergeHooks(path.join(repo, dst), JSON.parse(template(src, spec.skill)));
    touched.push(dst);
  }
  for (const [src, dst] of spec.files ?? []) {
    write(path.join(repo, dst), template(src, spec.skill));
    touched.push(dst);
  }
  for (const [src, dst] of spec.blocks ?? []) {
    addBlock(path.join(repo, dst), template(src, spec.skill));
    touched.push(dst);
  }
  return touched;
}

function fail(message, code = 1) {
  console.error(`cadence-orchestrator: ${message}`);
  process.exit(code);
}

const NAMES = Object.keys(TARGETS).sort().join("|");
const USAGE = `usage: cadence-orchestrator [--target <${NAMES}|all>] [--repo <path>] [--catalog <file.md>]...
       cadence-orchestrator doctor --target <...|all> [--repo <path>]
       cadence-orchestrator status [--repo <path>] [--hours <n>] [--state-dir <path>]
       cadence-orchestrator dora [--repo <path>] [--since <date>] [--deploys tags|merges|npm] [--include-prereleases] [--json]

Vendors the tpm skill and its guard hooks into the git repository you're in (or the one at --repo), for --target
or, without it, every editor the repo has config for (or else the agent running it). Re-running is safe.
\`doctor\` checks an installed target (files, hook config, python3, simulated hook events) and changes nothing.
\`dora\` computes DORA's delivery metrics from git (read-only).
\`status\` reports what's installed and whether hooks have been seen firing in a live session (default: last 24 h).`;

const FLAGS = ["--target", "--repo", "--catalog", "--state-dir", "--since", "--deploys", "--json",
  "--include-prereleases", "--hours", "-h", "--help"];

function parseArgs(argv, mode) {
  const opts = { repo: null, catalog: [], hours: 24, stateDir: "", since: null, deploys: "tags", json: false };
  for (let i = 0; i < argv.length; i++) {
    const [flag, inline] = argv[i].split(/=(.*)/s, 2);
    const value = () => inline ?? argv[++i] ?? fail(`${flag} needs a value\n${USAGE}`, 2);
    if (flag === "--target") opts.target = value();
    else if (flag === "--repo") {
      // A bare --repo (last, or followed by a known flag) means "here", like no --repo at all.
      const next = argv[i + 1];
      const bare = inline === undefined && (next === undefined || FLAGS.includes(next.split("=")[0]));
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
    } else if (flag === "--json" && mode === "dora") opts.json = true;
    else if (flag === "--include-prereleases" && mode === "dora") opts.includePrereleases = true;
    else if (flag === "--hours" && mode === "status") {
      opts.hours = Number(value());
      if (!(opts.hours > 0)) fail(`--hours needs a positive number\n${USAGE}`, 2);
    }
    else if (flag === "-h" || flag === "--help") {
      console.log(USAGE);
      process.exit(0);
    } else if (["--catalog", "--hours", "--target", "--state-dir", "--since", "--deploys", "--json", "--include-prereleases"].includes(flag)) {
      fail(`${mode === "install" ? "install" : mode} doesn't take ${flag}\n${USAGE}`, 2);
    } else fail(`unknown argument ${argv[i]}\n${USAGE}`, 2);
  }
  if (mode === "status" || mode === "dora") {
    if (opts.target) fail(`${mode} doesn't take --target\n${USAGE}`, 2);
    return opts;
  }
  if (!opts.target && mode === "doctor") fail(`--target is required\n${USAGE}`, 2);
  if (opts.target && opts.target !== "all" && !(opts.target in TARGETS)) fail(`unknown target ${opts.target}\n${USAGE}`, 2);
  return opts;
}

const argv = process.argv.slice(2);
const mode = ["doctor", "status", "dora"].includes(argv[0]) ? argv[0] : "install";
const isDoctor = mode === "doctor";
const opts = parseArgs(mode === "install" ? argv : argv.slice(1), mode);
// --repo <path> must be a repository root. Without it, the repository containing the current folder (the nearest
// folder up with a .git). Never the home directory, even when it's a git repository (dotfiles).
function findRepo(explicit) {
  const real = (p) => (exists(p) ? fs.realpathSync(p) : p);
  const home = real(os.homedir());
  let repo = explicit && path.resolve(explicit);
  if (repo && !exists(path.join(repo, ".git"))) fail(`${repo} is not a git repository root`);
  for (let dir = process.cwd(); !repo; dir = path.dirname(dir)) {
    if (exists(path.join(dir, ".git"))) repo = dir;
    else if (path.dirname(dir) === dir) fail(`${process.cwd()} is not inside a git repository`);
  }
  if (real(repo) === home) fail(`${repo} is your home directory; run this inside a project's repository`);
  return repo;
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
  const { lines, ok } = status(repo, TARGETS, opts.hours, opts.stateDir);
  for (const l of lines) console.log(l);
  process.exit(ok ? 0 : 1);
}
if (isDoctor) {
  const { doctor, installed } = await import("./doctor.mjs");
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
  for (const r of results) {
    const mark = r.skip ? "skip" : r.ok ? "ok  " : "FAIL";
    console.log(`${mark} ${r.name}${r.ok || !r.detail ? "" : `: ${r.detail}`}`);
  }
  const failed = results.filter((r) => !r.ok).length;
  const ran = results.filter((r) => !r.skip).length;
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
const chosen = opts.target ? { targets: opts.target === "all" ? Object.keys(TARGETS).sort() : [opts.target] } : detect();
const targets = chosen.targets;
const guarded = targets.filter((t) => hasGuard(TARGETS[t]));
console.log(`Installing into ${repo}${chosen.how ? ` for ${targets.join(", ")} (${chosen.how})` : ""}`);
const py = guarded.length ? spawnSync("python3", ["--version"], { stdio: "ignore" }) : { status: 0 };
if (py.error || py.status !== 0) {
  console.error("warning: python3 is not on PATH. The guard hooks run python3 and will not work until it is installed.");
}
const copied = new Set();
for (const t of targets) {
  console.log(`${t}: ${install(repo, t, copied).join(", ")}${hasGuard(TARGETS[t]) ? "" : " (instructions only, no guard)"}`);
}
addGitignore(repo);
if (opts.catalog.length) console.log(`catalog: ${addCatalogs(repo, opts.catalog).join(", ")}`);
console.log("Done. Review and commit the changes; see README for per-platform notes.");
if (guarded.length) console.log("Reload once: start a new chat or session in this repo, so the hooks load (approve them if asked).");
for (const t of targets) {
  // Codex has no project slash commands; it mentions skills with $ (https://learn.chatgpt.com/docs/build-skills).
  console.log(`${t}: start with ${t === "codex" ? "$tpm" : "/tpm"}${hasGuard(TARGETS[t]) ? "" : " (instructions only)"}`);
}
if (guarded.length) console.log("Then check the guard is running: npx cadence-orchestrator status");
