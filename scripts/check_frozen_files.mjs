#!/usr/bin/env node
// Byte-frozen files: working copies of content that lives on-chain. Each
// entry pins the sha256 the chain records for those bytes (sha256Decoded in
// the sibling receipts.json where one exists). A formatter pass or theme
// sweep that touches one of these silently voids the mirror guarantee — and
// push-to-main deploys straight to Pages — so CI fails on the first drifted
// byte. Never "fix" a failure by editing the hash: restore the bytes.
// Usage: node scripts/check_frozen_files.mjs   (exit 0 = all frozen files intact)
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

// [file, expected sha256 of the on-chain decoded bytes, receipts.json carrying it]
const FROZEN = [
  // etched delegation scroll ddaf75da406f8ffe6e8702f9821c1c3b883c390e785cd8acb973e73397234da8#0
  ["neon-door.html",
   "33d170ee9d7b35c707cb3631bfffbbea4f2ec57a3ba7e43c4c853dff7740341b", null],
  ["examples/beacn-leaks-000/beacn-leaks-000-manifesto.html",
   "025a81aeffe8aed98868b89b8f04a1f137f698362cfebafd2f8b5a56312d49b2",
   "examples/beacn-leaks-000/receipts.json"],
  ["examples/beacn-leaks-001/beacn-leaks-001-undeniable.html",
   "5917a884f449fd1c76fc0241791468a37b2b54883c0b8b98022a9f372f7d68b9",
   "examples/beacn-leaks-001/receipts.json"],
  ["examples/beacn-leaks-002/beacn-leaks-002-archives-blinked.html",
   "16612dfb6cef652e23014fecba3108996edb76c1d62d37562a2d799cb7165a55",
   "examples/beacn-leaks-002/receipts.json"],
  ["examples/card-catalog/card-catalog.csv",
   "bd11925a30f925f065345717f5c504992564c24899695a9c1720a83fb7baf9fb",
   "examples/card-catalog/receipts.json"],
  ["examples/eternal-scroll-tutorial/eternal-scroll-tutorial.html",
   "65824f624bc58140a33123d3e2383ea408135e5db666fcb8a0759b2846447dd2",
   "examples/eternal-scroll-tutorial/receipts.json"],
  ["examples/ledger-scrolls-000/ledger-scrolls-000-the-library-opens.html",
   "19ba8fccd3bd7e5ac997c3a4a0ff768a2699959bfd3bcf9db2ae073c09fe5013",
   "examples/ledger-scrolls-000/receipts.json"],
  ["examples/ledger-scrolls-theme/ledger-scrolls-theme.ogg",
   "8bd5c906744197d94a7252f2607f671037b426eea18a05fa39330a85145b06e7",
   "examples/ledger-scrolls-theme/receipts.json"],
  ["examples/legal-0001/legal-0001-declaration.html",
   "8c95db4bb4248d82d3d5c4bb49dfe0200d779f4b6905cd3b5649fcb847378bc1",
   "examples/legal-0001/receipts.json"],
  ["examples/protocol-one-pager/ledger-scrolls-one-pager.pdf",
   "89de5c64b0d2a05b0199875399a47506a75554d0d8613b0d88889667d2122adb",
   "examples/protocol-one-pager/receipts.json"],
  ["examples/the-reader/reader.html",
   "a824298dc5ced0aad1954c7d8d40bb6dda09debf402f062ab402dcebbb6a9215",
   "examples/the-reader/receipts.json"],
];

let failed = false;
for (const [file, expected, receipts] of FROZEN) {
  let got;
  try {
    got = createHash("sha256").update(readFileSync(join(root, file))).digest("hex");
  } catch (error) {
    console.error(`FAIL ${file}: ${error.message}`);
    failed = true;
    continue;
  }
  const ok = got === expected;
  console.log(`${ok ? "ok  " : "FAIL"} ${file}`);
  if (!ok) {
    failed = true;
    console.error(`     expected ${expected}\n     got      ${got}`);
  }
  if (receipts) {
    const r = JSON.parse(readFileSync(join(root, receipts), "utf8"));
    const recorded = r.sha256Decoded ?? r.plan?.sha256Decoded;
    if (recorded !== expected) {
      failed = true;
      console.error(`FAIL ${receipts}: sha256Decoded ${recorded} does not match pinned ${expected}`);
    }
  }
}
if (failed) process.exit(1);
console.log(`\n${FROZEN.length} frozen files intact`);
