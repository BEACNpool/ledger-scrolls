# Ledger Scrolls Conformance Suite

Canonical fixture corpus that pins down the protocol's byte-level behavior.
Any implementation (JS, Python, or third-party) must produce the same results
on these vectors. Specs and code drift; fixtures do not.

## Running

Both runners are dependency-free (stdlib only) and exercise the same
`manifest.json` corpus:

```bash
python3 conformance/run_conformance.py
node conformance/run_conformance.mjs
```

Exit code is non-zero on any failure, so both commands are CI-ready.

## What is covered

| Area | Fixtures | Verifies |
|---|---|---|
| Payloads | `fixtures/payloads/` | SHA-256 of raw bytes; deterministic gzip (mtime=0) round-trip |
| Standard datums | `fixtures/datums/` | CBOR byte-string decoding, both indefinite-length (≤64-byte chunks, per `registry/spec/cardano-utxo-datum.md`) and definite-length |
| CIP-25 pages | `fixtures/cip25/` | Page ordering by `i`, `0x`-prefix stripping, segment concatenation, manifest exclusion, gzip detection, full-file and gzip hashes |
| Pointers | `fixtures/pointers/valid`, `fixtures/pointers/invalid` | Canonical pointer kinds accepted (incl. deprecated aliases), malformed pointers rejected |
| Registry | `fixtures/registry/` | Canonical JSON serialization (sorted keys, no whitespace) and its SHA-256 |

## Adding vectors

1. Add the fixture file under `fixtures/`.
2. Record the expected hashes in `manifest.json`.
3. Make sure **both** runners pass.

Real mainnet receipts (tx hashes, policy IDs) may be used in pointer fixtures
— for example `fixtures/pointers/valid/utxo-inline-datum-bytes-v1.json` points
at the live Hosky PNG UTxO — but runners must never require network access:
everything here verifies offline.
