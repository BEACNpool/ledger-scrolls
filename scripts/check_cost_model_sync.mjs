#!/usr/bin/env node
// Asserts the cost-model constants embedded in calculator.html and media.html
// are identical, so the two pages can never quote different prices.
// Usage: node scripts/check_cost_model_sync.mjs   (exit 0 = in sync)
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function extractModel(file) {
  const html = readFileSync(join(root, file), "utf8");
  const m = html.match(/const P = \{([\s\S]*?)\};/);
  if (!m) throw new Error(`${file}: no "const P = {...}" block found`);
  const entries = {};
  for (const line of m[1].split("\n")) {
    const clean = line.replace(/\/\/.*$/, "").replace(/\/\*.*?\*\//g, "");
    for (const kv of clean.matchAll(/([A-Za-z_]\w*)\s*:\s*([\d.]+)/g)) {
      entries[kv[1]] = Number(kv[2]);
    }
  }
  return entries;
}

const calc = extractModel("calculator.html");
const media = extractModel("media.html");

let failures = 0;
for (const [k, v] of Object.entries(media)) {
  if (!(k in calc)) { console.error(`FAIL ${k}: in media.html but not calculator.html`); failures++; }
  else if (calc[k] !== v) { console.error(`FAIL ${k}: media.html=${v} calculator.html=${calc[k]}`); failures++; }
  else console.log(`ok   ${k} = ${v}`);
}
// media.html only needs the chain/standard subset; calculator-only keys (legacy NFT lane) are fine.
if (failures) { console.error(`\n${failures} constant(s) out of sync`); process.exit(1); }
console.log(`\ncost model in sync: ${Object.keys(media).length} shared constants match`);
