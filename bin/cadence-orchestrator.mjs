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
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CORE = path.join(ROOT, "core");
const ADAPTERS = path.join(ROOT, "adapters");
const MARK = "skills/tpm/scripts/shim_"; // identifies our hook entries on re-install
const BLOCK = /<!-- cadence-orchestrator:tpm begin -->[\s\S]*?<!-- cadence-orchestrator:tpm end -->\n?/g;

const TARGETS = {
  claude: { skill: ".claude/skills/tpm", hooks: [["claude/settings.hooks.json", ".claude/settings.json"]] },
  codex: {
    skill: ".agents/skills/tpm",
    hooks: [["codex/hooks.json", ".codex/hooks.json"]],
    blocks: [["codex/AGENTS.pointer.md", "AGENTS.md"]],
  },
  copilot: { skill: ".github/skills/tpm", hooks: [["copilot/hooks.json", ".github/hooks/tpm.json"]] },
  cursor: {
    skill: ".agents/skills/tpm",
    hooks: [["cursor/hooks.json", ".cursor/hooks.json"]],
    files: [["cursor/tpm.mdc", ".cursor/rules/tpm.mdc"]],
  },
  gemini: {
    skill: ".agents/skills/tpm",
    hooks: [["gemini/settings.hooks.json", ".gemini/settings.json"]],
    blocks: [["gemini/GEMINI.pointer.md", "GEMINI.md"]],
  },
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

function copySkill(repo, target, skill) {
  const dest = path.join(repo, skill);
  let text = read(path.join(CORE, "SKILL.md"));
  if (target === "claude") {
    // Claude Code only: the user, not the model, starts it (the guard arms on that).
    text = text.replace("\n---\n", "\ndisable-model-invocation: true\n---\n");
  }
  write(path.join(dest, "SKILL.md"), text);
  copyDir(path.join(CORE, "references"), path.join(dest, "references"));
  fs.mkdirSync(path.join(dest, "scripts"), { recursive: true });
  for (const name of ["guard.py", "runtime.py", "tasks_check.py"]) {
    fs.copyFileSync(path.join(CORE, "scripts", name), path.join(dest, "scripts", name));
  }
  fs.copyFileSync(path.join(ADAPTERS, target, "shim.py"), path.join(dest, "scripts", `shim_${target}.py`));
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

function install(repo, target) {
  const spec = TARGETS[target];
  copySkill(repo, target, spec.skill);
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
  addGitignore(repo);
  return touched;
}

function fail(message, code = 1) {
  console.error(`cadence-orchestrator: ${message}`);
  process.exit(code);
}

const USAGE = `usage: cadence-orchestrator --target <${Object.keys(TARGETS).sort().join("|")}|all> [--repo <path>] [--catalog <file.md>]...
       cadence-orchestrator doctor --target <...|all> [--repo <path>]

Vendors the tpm skill and its guard hooks into a git repository. Re-running is safe.
\`doctor\` checks an installed target (files, hook config, python3, simulated hook events) and changes nothing.`;

function parseArgs(argv) {
  const opts = { repo: ".", catalog: [] };
  for (let i = 0; i < argv.length; i++) {
    const [flag, inline] = argv[i].split(/=(.*)/s, 2);
    const value = () => inline ?? argv[++i] ?? fail(`${flag} needs a value\n${USAGE}`, 2);
    if (flag === "--target") opts.target = value();
    else if (flag === "--repo") opts.repo = value();
    else if (flag === "--catalog") opts.catalog.push(value());
    else if (flag === "-h" || flag === "--help") {
      console.log(USAGE);
      process.exit(0);
    } else fail(`unknown argument ${argv[i]}\n${USAGE}`, 2);
  }
  if (!opts.target) fail(`--target is required\n${USAGE}`, 2);
  if (opts.target !== "all" && !(opts.target in TARGETS)) fail(`unknown target ${opts.target}\n${USAGE}`, 2);
  return opts;
}

const argv = process.argv.slice(2);
const isDoctor = argv[0] === "doctor";
const opts = parseArgs(isDoctor ? argv.slice(1) : argv);
const repo = path.resolve(opts.repo);
if (!exists(path.join(repo, ".git"))) fail(`${repo} is not a git repository root`);
if (isDoctor) {
  const { doctor } = await import("./doctor.mjs");
  const targets = opts.target === "all" ? Object.keys(TARGETS).sort() : [opts.target];
  const results = targets.flatMap((t) => doctor(repo, t, TARGETS[t]));
  for (const r of results) {
    const mark = r.skip ? "skip" : r.ok ? "ok  " : "FAIL";
    console.log(`${mark} ${r.name}${r.ok || !r.detail ? "" : `: ${r.detail}`}`);
  }
  const failed = results.filter((r) => !r.ok).length;
  const ran = results.filter((r) => !r.skip).length;
  console.log(failed ? `${failed} check(s) failed.` : `All ${ran} checks passed.`);
  process.exit(failed ? 1 : 0);
}
const py = spawnSync("python3", ["--version"], { stdio: "ignore" });
if (py.error || py.status !== 0) {
  console.error("warning: python3 is not on PATH. The guard hooks run python3 and will not work until it is installed.");
}
const targets = opts.target === "all" ? Object.keys(TARGETS).sort() : [opts.target];
for (const t of targets) console.log(`${t}: ${install(repo, t).join(", ")}`);
if (opts.catalog.length) console.log(`catalog: ${addCatalogs(repo, opts.catalog).join(", ")}`);
console.log("Done. Review and commit the changes; see README for per-platform notes.");
