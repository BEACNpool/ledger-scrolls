#!/usr/bin/env node
// Every page hardcodes its own Koios CORS-mirror list, so a mirror rollout
// must edit them in lockstep. Asserts the lists agree across pages (set
// equality, mainnet and preview compared separately, pages compared against
// each other — no canonical list to go stale), and that no page or service
// worker reaches api.koios.rest / preview.koios.rest directly: browsers only
// ever get the CORS worker (direct Koios has no CORS header — the regression
// that once broke every reader). neon-door.html is byte-frozen on-chain, so
// its list is reported but never enforced.
// Usage: node scripts/check_mirror_lists.mjs   (exit 0 = lists in sync, mirror-only)
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const FROZEN = new Set(["neon-door.html"]);

const pages = readdirSync(root)
  .filter((f) => f.endsWith(".html") && !f.includes(".bak-"))
  .sort()
  .concat(["build-a-reader/index.html"]);
const workers = readdirSync(root).filter((f) => /^sw[\w-]*\.js$/.test(f)).sort();

function inlineJs(file) {
  const html = readFileSync(join(root, file), "utf8");
  return [...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/gi)]
    .filter((m) => !/\bsrc\s*=/i.test(m[1]) && !/application\/ld\+json/i.test(m[1]))
    .map((m) => m[2])
    .join("\n");
}

function mirrorLists(js) {
  const urls = [...js.matchAll(/["'`](https:\/\/[^"'`\s]+?\/api\/v1)["'`]/g)].map((m) => m[1]);
  return {
    mainnet: [...new Set(urls.filter((u) => !u.includes("/preview/")))].sort(),
    preview: [...new Set(urls.filter((u) => u.includes("/preview/")))].sort(),
  };
}

let failed = false;

// direct-Koios ban: pages and service workers
const DIRECT = /["'`]https?:\/\/(api|preview)\.koios\.rest/;
for (const file of pages.concat(workers)) {
  const js = file.endsWith(".js") ? readFileSync(join(root, file), "utf8") : inlineJs(file);
  const hit = js.match(DIRECT);
  const ok = !hit;
  console.log(`${ok ? "ok  " : "FAIL"} ${file} mirror-only`);
  if (!ok) { failed = true; console.error(`     direct Koios URL: ${hit[0].slice(1)}…`); }
}

// cross-page list consistency
const lists = pages
  .map((file) => ({ file, ...mirrorLists(inlineJs(file)) }))
  .filter((p) => p.mainnet.length || p.preview.length);
for (const net of ["mainnet", "preview"]) {
  const enforced = lists.filter((p) => !FROZEN.has(p.file) && p[net].length);
  if (!enforced.length) continue;
  const ref = enforced[0];
  for (const p of enforced) {
    const ok = JSON.stringify(p[net]) === JSON.stringify(ref[net]);
    console.log(`${ok ? "ok  " : "FAIL"} ${p.file} ${net} mirrors (${p[net].length})`);
    if (!ok) {
      failed = true;
      console.error(`     ${p.file}: ${p[net].join(", ")}\n     ${ref.file}: ${ref[net].join(", ")}`);
    }
  }
  for (const p of lists.filter((q) => FROZEN.has(q.file) && q[net].length)) {
    const same = JSON.stringify(p[net]) === JSON.stringify(ref[net]);
    console.log(`note ${p.file} ${net} mirrors ${same ? "match" : "DIFFER (frozen — not enforced)"}: ${p[net].join(", ")}`);
  }
}

if (failed) process.exit(1);
console.log(`\nmirror lists in sync across ${lists.filter((p) => !FROZEN.has(p.file)).length} pages; no direct Koios URLs`);
