#!/usr/bin/env node
// Render every media/*-card-source.html to its PNG at 1200x630 — the size X,
// Discord, Telegram, Slack and iMessage all crop their preview from.
//
//   node scripts/build_og_cards.mjs
//
// The PNGs are committed, so CI never runs this; it runs when a card changes.
// Needs Chromium and puppeteer-core. If puppeteer-core is not resolvable from
// this repo (it has no node_modules by design), point at one:
//   PUPPETEER_DIR=~/projects/webdev-toolkit/node_modules node scripts/build_og_cards.mjs
//
// The sources are loaded over a throwaway localhost server rather than file://,
// because a snap-packaged Chromium is confined and cannot read a file inside a
// dot-directory (this repo lives under ~/.openclaw/).
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join, extname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

const CARDS = [
  ["media/og-card-source.html", "media/og-card.png"],
  ["media/ledger-book-card-source.html", "media/ledger-book-card.png"],
  ["media/ledger-chess-card-source.html", "media/ledger-chess-card.png"],
];

const CHROME = ["/snap/bin/chromium", "/usr/bin/chromium", "/usr/bin/chromium-browser",
  "/usr/bin/google-chrome"].find(existsSync);
if (!CHROME) { console.error("no chromium binary found"); process.exit(1); }

const dirs = [process.env.PUPPETEER_DIR, join(root, "node_modules"),
  join(process.env.HOME || "", "projects/webdev-toolkit/node_modules")].filter(Boolean);
let puppeteer;
for (const d of dirs) {
  const pkgDir = join(d, "puppeteer-core");
  if (!existsSync(pkgDir)) continue;
  try {
    // resolve the real entry from the package manifest — its path has moved
    // between puppeteer versions, so do not hard-code it
    const manifest = JSON.parse(await readFile(join(pkgDir, "package.json"), "utf8"));
    const rel = manifest.exports?.["."]?.import || manifest.main;
    puppeteer = (await import(pathToFileURL(join(pkgDir, rel)).href)).default;
    break;
  } catch { /* try the next location */ }
}
if (!puppeteer) {
  console.error("puppeteer-core not found — set PUPPETEER_DIR=<path>/node_modules");
  process.exit(1);
}

const TYPES = { ".html": "text/html", ".png": "image/png", ".svg": "image/svg+xml",
  ".jpg": "image/jpeg", ".css": "text/css", ".js": "text/javascript" };
const server = createServer(async (req, res) => {
  try {
    const p = join(root, decodeURIComponent(new URL(req.url, "http://x").pathname));
    if (!p.startsWith(root)) { res.writeHead(403).end(); return; }
    const body = await readFile(p);
    res.writeHead(200, { "Content-Type": TYPES[extname(p)] || "application/octet-stream" });
    res.end(body);
  } catch { res.writeHead(404).end(); }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: "new", args: ["--no-sandbox", "--disable-gpu"],
});
for (const [src, out] of CARDS) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1200, height: 630, deviceScaleFactor: 1 });
  const resp = await page.goto(`${base}/${src}`, { waitUntil: "networkidle0" });
  if (!resp || !resp.ok()) throw new Error(`${src}: HTTP ${resp && resp.status()}`);
  await page.screenshot({ path: join(root, out), type: "png" });
  await page.close();
  console.log(`ok   ${out}`);
}
await browser.close();
server.close();
console.log(`\n${CARDS.length} share card(s) rendered at 1200x630`);
