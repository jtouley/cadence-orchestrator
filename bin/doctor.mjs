// `cadence-orchestrator doctor`: check an installed target without changing the repo.
//
// For each target: the skill files and hook config exist, every hook command points at an
// existing shim, python3 is on PATH, and the installed hook commands behave as expected on
// simulated events (arm, a main-thread Write, a subagent Write, and Stop where configured).
// The simulated events use a temporary state directory, which is removed afterwards.

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const SCRIPTS = ["guard.py", "runtime.py", "tasks_check.py"];
// Environment variables a platform's runtime consults for its state dir (see each shim's state_env).
const STATE_ENV = { claude: ["CLAUDE_PLUGIN_DATA"] };

// A target counts as installed if its shim or its hook entries are present.
export function installed(repo, target, spec) {
  if (fs.existsSync(path.join(repo, spec.skill, "scripts", `shim_${target}.py`))) return true;
  const hookFile = path.join(repo, spec.hooks[0][1]);
  return fs.existsSync(hookFile) && fs.readFileSync(hookFile, "utf8").includes(`shim_${target}.py`);
}

// Per platform: how to find hook commands in its config, and the events to simulate.
const PLATFORMS = {
  claude: {
    commands: (hooks, event) => (hooks[event] ?? []).flatMap((g) => (g.hooks ?? []).map((h) => h.command)),
    arm: ["UserPromptExpansion", { hook_event_name: "UserPromptExpansion", command_name: "tpm" }],
    tool: "PreToolUse",
    write: (sub) => ({
      hook_event_name: "PreToolUse",
      tool_name: "Write",
      tool_input: { file_path: "doctor-check.txt", content: "x" },
      ...(sub ? { agent_id: "doctor-subagent" } : {}),
    }),
    stop: ["Stop", { hook_event_name: "Stop", stop_hook_active: false, background_tasks: [] }],
    enforcing: true,
    denied: (r) => r.status === 2 && r.stderr.includes("TPM mode"),
    allowed: (r) => r.status === 0 && r.stdout.trim() === "",
  },
  copilot: {
    commands: (hooks, event) => (hooks[event] ?? []).map((h) => h.bash),
    arm: ["UserPromptSubmit", { hook_event_name: "UserPromptSubmit", prompt: "/tpm doctor" }],
    tool: "PreToolUse",
    write: (sub) => ({
      hook_event_name: "PreToolUse",
      tool_name: "Write",
      tool_input: { file_path: "doctor-check.txt", content: "x" },
      ...(sub ? { agent_id: "doctor-subagent" } : {}),
    }),
    enforcing: true,
    denied: (r) => r.status === 0 && /"permissionDecision":\s*"deny"/.test(r.stdout),
    allowed: (r) => r.status === 0 && r.stdout.trim() === "",
  },
  codex: {
    commands: (hooks, event) => (hooks[event] ?? []).flatMap((g) => (g.hooks ?? []).map((h) => h.command)),
    arm: ["UserPromptSubmit", { hook_event_name: "UserPromptSubmit", prompt: "$tpm doctor" }],
    tool: "PreToolUse",
    write: () => ({ hook_event_name: "PreToolUse", tool_name: "apply_patch", tool_input: { command: "patch" } }),
    advisory: (r) => r.status === 0 && r.stdout.includes("tpm advisory"),
  },
  cursor: {
    commands: (hooks, event) => (hooks[event] ?? []).map((h) => h.command),
    arm: ["beforeSubmitPrompt", { hook_event_name: "beforeSubmitPrompt", prompt: "/tpm doctor" }],
    tool: "preToolUse",
    write: () => ({ hook_event_name: "preToolUse", tool_name: "Write", tool_input: { path: "doctor-check.txt" } }),
    advisory: (r) => r.status === 0 && /"permission":\s*"allow"/.test(r.stdout) && r.stderr.includes("tpm advisory"),
  },
  gemini: {
    commands: (hooks, event) => (hooks[event] ?? []).flatMap((g) => (g.hooks ?? []).map((h) => h.command)),
    arm: ["BeforeAgent", { hook_event_name: "BeforeAgent", prompt: "/tpm doctor" }],
    tool: "BeforeTool",
    write: () => ({ hook_event_name: "BeforeTool", tool_name: "write_file", tool_input: { file_path: "doctor-check.txt" } }),
    advisory: (r) => r.status === 0 && r.stdout.includes("tpm advisory"),
  },
};

export function doctor(repo, target, spec) {
  const p = PLATFORMS[target];
  const results = [];
  const check = (name, ok, detail = "", skip = false) => results.push({ name: `${target}: ${name}`, ok, detail, skip });
  const shim = `${spec.skill}/scripts/shim_${target}.py`;

  for (const f of ["SKILL.md", ...SCRIPTS.map((s) => `scripts/${s}`), `scripts/shim_${target}.py`]) {
    const rel = `${spec.skill}/${f}`;
    check(`${rel} exists`, fs.existsSync(path.join(repo, rel)));
  }

  const [, hookFile] = spec.hooks[0];
  let hooks = null;
  try {
    hooks = JSON.parse(fs.readFileSync(path.join(repo, hookFile), "utf8")).hooks ?? {};
    check(`${hookFile} is valid JSON`, true);
  } catch (e) {
    check(`${hookFile} is valid JSON`, false, e.message);
  }
  const ours = (event) => (hooks ? p.commands(hooks, event).filter((c) => typeof c === "string" && c.includes(shim)) : []);
  const events = [p.arm[0], p.tool, ...(p.stop ? [p.stop[0]] : [])];
  for (const event of events) {
    check(`${event} hook points at ${shim}`, ours(event).length > 0, "not found in " + hookFile);
  }

  const py = spawnSync("python3", ["--version"], { encoding: "utf8" });
  check("python3 is on PATH", !py.error && py.status === 0, "the hooks run python3; without it they allow everything");

  // Where the real hooks keep state and advisory.log: ask the installed runtime.py directly (not the
  // shim, whose import-failure path prints its platform's "allow" output). Only an absolute path on a
  // STATE= line is accepted; if runtime.py is missing or broken this check fails and nothing is created.
  const resolver =
    "import sys, types\n" +
    "sys.dont_write_bytecode = True\n" +
    "sys.path.insert(0, sys.argv[1])\n" +
    "import runtime\n" +
    "print('STATE=' + runtime.state_dir(types.SimpleNamespace(state_env=tuple(sys.argv[2:]))))";
  const scripts = path.join(repo, spec.skill, "scripts");
  const where = spawnSync("python3", ["-B", "-c", resolver, scripts, ...(STATE_ENV[target] ?? [])], {
    encoding: "utf8",
    cwd: os.tmpdir(),
  });
  const line = (where.stdout ?? "").split("\n").find((l) => l.startsWith("STATE=")) ?? "";
  const realState = where.status === 0 ? line.slice("STATE=".length).trim() : "";
  let writable = false;
  if (realState && path.isAbsolute(realState)) {
    try {
      // Same as the runtime: create the directory if needed, then prove a file can be written there.
      fs.mkdirSync(realState, { recursive: true });
      const probe = path.join(realState, `.doctor-${process.pid}`);
      fs.writeFileSync(probe, "");
      fs.unlinkSync(probe);
      writable = true;
    } catch {}
  }
  const why = !realState
    ? `couldn't load ${spec.skill}/scripts/runtime.py: ${(where.stderr || "no output").trim().split("\n").at(-1)}`
    : !path.isAbsolute(realState)
      ? `runtime returned a relative path (${realState})`
      : "not writable: set CADENCE_STATE_DIR to a writable directory";
  check(
    `state dir ${realState || "(unresolved)"} is writable; advisory log: ${realState ? path.join(realState, "advisory.log") : "?"}`,
    writable,
    why,
  );

  const state = fs.mkdtempSync(path.join(os.tmpdir(), "cadence-doctor-"));
  const session = "doctor-" + process.pid;
  const run = (event, payload) => {
    const cmd = ours(event)[0];
    if (!cmd) return { status: -1, stdout: "", stderr: "no hook command" };
    const input = JSON.stringify({ session_id: session, conversation_id: session, cwd: repo, ...payload });
    const env = { ...process.env, CADENCE_STATE_DIR: state, CLAUDE_PROJECT_DIR: repo, GEMINI_PROJECT_DIR: repo };
    const r = spawnSync("bash", ["-c", cmd], { cwd: repo, input, env, encoding: "utf8", timeout: 20000 });
    return { status: r.status, stdout: r.stdout ?? "", stderr: r.stderr ?? "" };
  };
  const show = (r) => `exit ${r.status}; stdout ${JSON.stringify(r.stdout.trim()).slice(0, 160)}`;
  try {
    const armed = run(p.arm[0], p.arm[1]);
    check(`simulated ${p.arm[1].prompt?.split(" ")[0] ?? "/tpm"} arms the session`, armed.status === 0 && fs.existsSync(path.join(state, "tpm-armed", session)), show(armed));
    const main = run(p.tool, p.write(false));
    if (p.enforcing) {
      check("orchestrator Write is denied", p.denied(main), show(main));
      const sub = run(p.tool, p.write(true));
      check("subagent Write is allowed", p.allowed(sub), show(sub));
    } else {
      const logged = fs.existsSync(path.join(state, "advisory.log"));
      check("orchestrator write gets the advisory (never blocks)", p.advisory(main), show(main));
      check("advisory is logged", logged, "no advisory.log in the state directory");
      check("subagent Write (this platform doesn't mark subagents)", true, "", true);
    }
    if (p.stop) {
      const stop = run(p.stop[0], p.stop[1]);
      check("Stop with no running agents is allowed", stop.status === 0 && stop.stdout.trim() === "", show(stop));
    }
  } finally {
    fs.rmSync(state, { recursive: true, force: true });
  }
  return results;
}
