#!/usr/bin/env node
// Asserts media.html's static cost constants match calculator.html's REAL
// (post-applyPacking) model, so the two pages can never quote different prices.
// calculator.html is executed (with DOM stubs) to get the runtime truth —
// regex-comparing its `const P` literal missed the dynamic packing values.
// Usage: node scripts/check_cost_model_sync.mjs   (exit 0 = in sync)
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function runtimeModel() {
  const html = readFileSync(join(root, "calculator.html"), "utf8");
  const m = html.match(/<script>([\s\S]*?)<\/script>/);
  if (!m) throw new Error("calculator.html: no inline script");
  const stub = new Proxy(function () {}, {
    get: (t, p) => (p === Symbol.toPrimitive ? () => "" : stub),
    apply: () => stub,
    construct: () => stub,
  });
  // stubs as parameters (not global mutation — navigator is getter-only in ESM)
  const api = new Function(
    "document", "window", "navigator", "localStorage", "location", "fetch", "addEventListener",
    m[1] + "\n;return {P, PACK};"
  )(stub, stub, stub, stub, { hash: "", href: "", origin: "", pathname: "" },
    () => new Promise(() => {}), () => {});
  return api.P;   // post-applyPacking defaults (max_tx 16384, safety 400)
}

function staticModel(file) {
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

const calc = runtimeModel();
const media = staticModel("media.html");

let failures = 0;
for (const [k, v] of Object.entries(media)) {
  if (!(k in calc)) { console.error(`FAIL ${k}: in media.html but not calculator.html`); failures++; }
  else if (calc[k] !== v) { console.error(`FAIL ${k}: media.html=${v} calculator.html=${calc[k]}`); failures++; }
  else console.log(`ok   ${k} = ${v}`);
}
// media.html only needs the chain/standard subset; calculator-only keys (legacy NFT lane) are fine.
if (failures) { console.error(`\n${failures} constant(s) out of sync`); process.exit(1); }
console.log(`\ncost model in sync: ${Object.keys(media).length} shared constants match`);
