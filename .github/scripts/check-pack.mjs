#!/usr/bin/env node
// Fail if `npm pack` would ship anything outside package.json's `files` allowlist
// (plus the files npm always adds), or anything that should never ship.
import { execFileSync } from "node:child_process";
import fs from "node:fs";

const pkg = JSON.parse(fs.readFileSync("package.json", "utf8"));
const always = new Set(["package.json", "README.md", "LICENSE"]);
const allowed = (p) =>
  always.has(p) || pkg.files.some((f) => (f.endsWith("/") ? p.startsWith(f) : p === f));
const forbidden = /(^|\/)(tests?|evals|\.claude-plugin|__pycache__|node_modules)(\/|$)|\.pyc$|(^|\/)\.env/;

const [report] = JSON.parse(execFileSync("npm", ["pack", "--dry-run", "--json"], { encoding: "utf8" }));
const paths = report.files.map((f) => f.path).sort();
const bad = paths.filter((p) => !allowed(p) || forbidden.test(p));
const missing = pkg.files.filter((f) => !paths.some((p) => (f.endsWith("/") ? p.startsWith(f) : p === f)));

console.log(paths.join("\n"));
if (bad.length) console.error(`\nNot allowed in the package:\n  ${bad.join("\n  ")}`);
if (missing.length) console.error(`\nListed in "files" but not packed:\n  ${missing.join("\n  ")}`);
if (bad.length || missing.length) process.exit(1);
console.log(`\n${paths.length} files, all within the allowlist.`);
