#!/usr/bin/env node
// Parses every inline <script> on every root page (script goal via vm.Script,
// which catches a stray top-level return that Function() would mask) plus the
// service workers, then asserts the per-page protocol invariants — above all
// that EVERY tx-body encoder carries the upper validity bound (tip+3600) and
// that tip-less builds are refused. Enforced per encoder, not per page: a
// single page-wide match once let a second encoder ship without a TTL.
// Usage: node scripts/check_inline_js.mjs   (exit 0 = all pages pass)
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const pages = readdirSync(root)
  .filter((f) => f.endsWith(".html") && !f.includes(".bak-"))
  .sort()
  .concat(["build-a-reader/index.html"]);
const workers = readdirSync(root).filter((f) => /^sw[\w-]*\.js$/.test(f)).sort();

let failed = false;
for (const file of pages) {
  const html = readFileSync(join(root, file), "utf8");
  const scripts = [...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/gi)]
    .filter((m) => !/\bsrc\s*=/i.test(m[1]) && !/application\/ld\+json/i.test(m[1]))
    .map((m) => m[2]);
  try {
    for (const source of scripts) new vm.Script(source, { filename: file });
    console.log(`ok   ${file} inline JavaScript parses`);
  } catch (error) {
    failed = true;
    console.error(`FAIL ${file}: ${error.message}`);
  }
}
for (const file of workers) {
  try {
    new vm.Script(readFileSync(join(root, file), "utf8"), { filename: file });
    console.log(`ok   ${file} parses`);
  } catch (error) {
    failed = true;
    console.error(`FAIL ${file}: ${error.message}`);
  }
}

// Per-page invariants. `encoders` lists every tx-body builder on the page;
// each one must emit the body key 3 upper validity bound itself.
const TTL = /cU\(3\)\s*,\s*cU\(ttl\)/;
const INVARIANTS = {
  "calculator.html": {
    encoders: ["encBody", "encPageBody", "encManifestBody", "encPlainBody"],
    patterns: [
      ["ttl horizon is one hour", /TTL_HORIZON\s*=\s*3600/],
      ["tip fetched before every build", /fetchTipSlot/],
      ["tip-less builds refused", /refusing to build an open-ended transaction/],
    ],
  },
  "ledger-chess.html": {
    encoders: ["encClaimBody"],
    patterns: [
      ["claim ttl = tip + one hour", /tipSlot\+3600/],
      ["tip-less claims refused", /refusing to build an open-ended claim/],
    ],
  },
  "ledger-book.html": {
    encoders: ["encMintBody", "encClaimBody"],
    patterns: [
      ["v2 protocol marker", /BOOK_NFT_PROTOCOL\s*=\s*"ledger-book-v2"/],
      ["expiring native policy", /cU\(5\).*expirySlot/],
      ["raw asset-name key", /BOOK\.keyHex/],
      ["tip-less signatures refused", /refusing to build an open-ended signature/],
      ["unbounded mint policy refused", /refusing to create an unbounded mint policy/],
      ["no 40-transfer truncation", /slice\(0,\s*40\)/, true],
      ["no 800-signature truncation", /slice\(0,\s*800\)/, true],
    ],
  },
};

// slice one top-level `function name(...)` — encoders are adjacent top-level fns
function fnBlock(html, name) {
  const start = html.indexOf(`function ${name}(`);
  if (start < 0) return null;
  const end = html.indexOf("\nfunction ", start + 1);
  return html.slice(start, end < 0 ? start + 4000 : end);
}

for (const [file, { encoders, patterns }] of Object.entries(INVARIANTS)) {
  const html = readFileSync(join(root, file), "utf8");
  for (const name of encoders) {
    const block = fnBlock(html, name);
    const ok = block !== null && TTL.test(block);
    console.log(`${ok ? "ok  " : "FAIL"} ${file}: ${name} carries upper validity bound`);
    if (!ok) failed = true;
  }
  for (const [name, pattern, inverted] of patterns) {
    const ok = inverted ? !pattern.test(html) : pattern.test(html);
    console.log(`${ok ? "ok  " : "FAIL"} ${file}: ${name}`);
    if (!ok) failed = true;
  }
}

// Golden vector independently checked with cardano-cli 11.0.0.0. This executes
// the exact in-page CBOR and Blake2b implementation, not a second copy.
try {
  const book = readFileSync(join(root, "ledger-book.html"), "utf8");
  const helpers = book.match(/var u8 =[\s\S]*?var catB =[\s\S]*?return o; \};/)[0];
  const blake = book.match(/var B2IV=[\s\S]*?function blake2b256\(input\)\{[^}]+\}/)[0];
  const cbor = book.match(/function cH\(n,mt\)[\s\S]*?var cTg=function\(n\)\{return cH\(n,6\);\};/)[0];
  const policyId = Function(`${helpers}\n${blake}\n${cbor}\n` + String.raw`
    const key=Uint8Array.from({length:28},(_,i)=>i), expiry=192075000;
    const sig=catB([u8([0x82,0x00,0x58,0x1c]),key]);
    const before=catB([cAr(2),cU(5),cU(expiry)]);
    const script=catB([cAr(2),cU(1),cAr(2),sig,before]);
    return Array.from(blake2bN(catB([u8([0]),script]),28),x=>x.toString(16).padStart(2,'0')).join('');
  `)();
  const expected="ceb8c796bf6662b35765d7403695b5ec9566efecc782b92543efb760";
  const ok=policyId===expected;
  console.log(`${ok ? "ok  " : "FAIL"} ledger-book.html: v2 policy id matches cardano-cli golden vector`);
  if(!ok)failed=true;
} catch(error) {
  console.error(`FAIL v2 policy golden vector: ${error.message}`); failed=true;
}
process.exit(failed ? 1 : 0);
