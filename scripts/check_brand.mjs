#!/usr/bin/env node
/* One house, many rooms — enforced.
 *
 * The nav was the only chrome in this repo that never rotted, because a script owned
 * it and CI proved it. Everything a human owned drifted: two stacked logos on the Book
 * page, a token literally named --purple holding the house blue, a template lightning
 * bolt shipping as the favicon on every page, and a PWA whose start_url opened the
 * calculator instead of the library.
 *
 * So the brand is a fixture now. These strings are dead in the UI. If one comes back,
 * the build fails.
 *
 * IMPORTANT — what is deliberately NOT checked:
 *   registry/, docs/, examples/, conformance/, tools/, viewers/, koios-viewer/
 *   and neon-door.html.
 * Those are specs, fixtures, and bytes the chain froze. The on-chain record says
 * LEDGER_SCROLLS, LS_REGISTRY_V7 and /ledger-scrolls/ and it says so FOREVER — that is
 * the point of the chain, not a bug to sweep. We renamed the sign on the door, not the
 * ledger. Specs and code drift; fixtures do not.
 */
import { readFileSync } from "node:fs";

// UI surfaces only — the pages a human actually reads.
const FILES = [
  "index.html", "calculator.html", "ledger-book.html", "ledger-chess.html",
  "media.html", "leaks.html", "vault-tool.html", "build-a-reader/index.html",
  "manifest.webmanifest", "favicon.svg", "sw.js",
];

/* Banned ANYWHERE in a UI file. These have no protocol meaning — they are pure
   display-layer rot, so there is no legitimate reason for them to reappear. */
const BANNED_EVERYWHERE = [
  ["--purple",     "renamed to --accent; the value was always the house blue #2f6bff"],
  ["#863bff",      "the dead violet LS medallion / the template favicon"],
  ["Scroll Press", "the orphaned second PWA name — the writer is The Mint"],
  ["Main Viewer",  'the front door is "The Library"'],
];

/* Banned only in <head> — the shareable identity.
 *
 * THIS SCOPE IS LOAD-BEARING, do not widen it to the whole file. "Ledger Book" is
 * also the on-chain CIP-25 `Type` constant that ledger-book-v2 REQUIRES: every minted
 * book carries it and the reader validates against it (md.Type !== "Ledger Book"
 * throws). The chain keeps the names it was minted with — that is the point of the
 * chain, not drift. The display layer renames; the protocol constant never does.
 *
 * The bug this catches is the one that actually shipped: the endorsement was INVERTED.
 * The utility pages nobody shares carried "— Ledger Scrolls" in their <title>, while
 * the products people DO share (Book, Board, Vault) dropped it — so a Book link posted
 * anywhere carried no signal about whose house it came from. */
const BANNED_IN_HEAD = [
  ["Ledger Book",  'the room is "The Book" (the on-chain Type constant stays — body JS only)'],
  ["Ledger Chess", 'the room is "The Board"'],
  ["Vault Tool",   'the room is "The Vault"'],
];

const report = (f, src, needle, why) => {
  const line = src.slice(0, src.indexOf(needle)).split("\n").length;
  console.error(`DRIFT ${f}:${line}  "${needle}" — ${why}`);
};

let bad = 0;
for (const f of FILES) {
  let src;
  try { src = readFileSync(f, "utf8"); }
  catch { console.error(`MISSING ${f}`); bad++; continue; }

  for (const [needle, why] of BANNED_EVERYWHERE) {
    if (src.includes(needle)) { report(f, src, needle, why); bad++; }
  }

  const headEnd = src.indexOf("</head>");
  const head = headEnd === -1 ? "" : src.slice(0, headEnd);
  for (const [needle, why] of BANNED_IN_HEAD) {
    if (head.includes(needle)) { report(f, head, needle, why); bad++; }
  }

  // Every shareable page must name the house in its title — that is the whole fix.
  if (f.endsWith(".html") && head && !/<title>[^<]*Ledger Scrolls/.test(head) && !/<title>[^<]*BEACN/.test(head)) {
    console.error(`DRIFT ${f}  — <title> does not name the house; a shared link must say whose it is`);
    bad++;
  }
}

// The lockup must actually be present, not merely un-violated: a page that lost its
// chrome entirely would otherwise pass by saying nothing at all.
for (const f of FILES.filter(f => f.endsWith(".html"))) {
  const src = readFileSync(f, "utf8");
  if (!src.includes('class="ls-brand"')) {
    console.error(`DRIFT ${f}  — no house lockup; run: python3 scripts/sync_brand.py`);
    bad++;
  }
}

if (bad) {
  console.error(`\n${bad} brand drift(s). The house is Ledger Scrolls; the pages are rooms.`);
  process.exit(1);
}
console.log(`brand consistent across ${FILES.length} UI surfaces`);
