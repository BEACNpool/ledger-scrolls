#!/usr/bin/env node
import { readFileSync } from "node:fs";

const files = ["index.html", "calculator.html", "ledger-book.html", "ledger-chess.html", "leaks.html"];
let failed = false;
for (const file of files) {
  const html = readFileSync(file, "utf8");
  const scripts = [...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/gi)]
    .filter((m) => !/application\/ld\+json/i.test(m[1]))
    .map((m) => m[2]);
  try {
    for (const source of scripts) Function(source);
    console.log(`ok   ${file} inline JavaScript parses`);
  } catch (error) {
    failed = true;
    console.error(`FAIL ${file}: ${error.message}`);
  }
}

const book = readFileSync("ledger-book.html", "utf8");
const invariants = [
  ["v2 protocol marker", /BOOK_NFT_PROTOCOL\s*=\s*"ledger-book-v2"/],
  ["expiring native policy", /cU\(5\).*expirySlot/],
  ["transaction upper validity bound", /cU\(3\),\s*cU\(ttl\)/],
  ["raw asset-name key", /BOOK\.keyHex/],
  ["no 40-transfer truncation", /slice\(0,\s*40\)/, true],
  ["no 800-signature truncation", /slice\(0,\s*800\)/, true],
];
for (const [name, pattern, inverted] of invariants) {
  const ok = inverted ? !pattern.test(book) : pattern.test(book);
  console.log(`${ok ? "ok  " : "FAIL"} ${name}`);
  if (!ok) failed = true;
}

// Golden vector independently checked with cardano-cli 11.0.0.0. This executes
// the exact in-page CBOR and Blake2b implementation, not a second copy.
try {
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
  console.log(`${ok ? "ok  " : "FAIL"} v2 policy id matches cardano-cli golden vector`);
  if(!ok)failed=true;
} catch(error) {
  console.error(`FAIL v2 policy golden vector: ${error.message}`); failed=true;
}
process.exit(failed ? 1 : 0);
