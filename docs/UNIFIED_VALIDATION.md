# Unified release validation

The browser suite exercises the actual standalone app pages with synthetic data
and wallets. Every external request is intercepted; signing stops at a synthetic
sentinel before any signature is produced. It cannot publish a transaction.

```bash
python3 -m http.server 8937 --bind 127.0.0.1
# In another terminal, with puppeteer-core installed in an external test environment:
PUPPETEER_MODULE=/path/to/node_modules/puppeteer-core \
CHROMIUM_BIN=/path/to/chromium \
node scripts/browser-regression.mjs http://127.0.0.1:8937/ /path/to/results
```

For the GitHub Pages subdirectory case, optionally set `PAGES_PREFIX_BASE` to a
served copy of the same site beneath `/ledger-scrolls/`. The suite follows both
product links and checks that their brand assets stay beneath that prefix.

The independent fixture encoder checks transaction outputs, fees, expiry, and
token conservation, including a quantity above JavaScript's safe-integer range.
Python hashlib independently computes the native-policy test hash. Other cases
cover malformed CBOR, fingerprint mismatch, absent commitments, sandboxing,
policy evidence, historical keeper payment, missing history, changed keeper and
network, draft restoration, and attached work encoding/tamper detection.
Sibling-product cases cover standalone Book minting without a Scroll, Book
starters, saved Books and the shared shelf, cross-tab bookmark changes, and each
product's own identity and active navigation.

The suite does not establish real wallet compatibility or independent Cardano
inclusion proofs. A mainnet acceptance mint for the new subject extension has
not been performed.

Existing required checks remain in `.github/workflows/conformance.yml`:
Python/JavaScript protocol vectors, schemas, Python reader/tooling unit tests,
shell and inline-JavaScript syntax, cost-model synchronization, generated
navigation, mirror lists, frozen on-chain originals, and whitespace checks.

Fixture checks and live read-only validation are recorded in separate reports.
Live mainnet acceptance reads during this rebuild reconstructed the existing
18,182-byte tutorial and matched its published SHA-256, and opened the existing
Book_v2_Acceptance with an expired policy, supply one, and its existing entry.
These were reads only. No signing key or production-node service was involved.
