# Published Registry Head — LS_REGISTRY_V6 (2026-07-10)

The live public registry is an **NFT**, not a datum: a Registry Head under the
LEDGER_SCROLLS library policy, with the scroll list in its mint transaction's
metadata label `22027`. Spec: [`../spec/registry-nft-v2.md`](../spec/registry-nft-v2.md).

- **Library policy:** `8d6d38b3967028a15fc0e401b53c73a75ac654affc3f817c750c8b80`
- **Current head:** `LS_REGISTRY_V6` (721 `Type: "Registry Head"`, `Version: 6`)
- **Mint tx:** `955c6d2aa84b1d1d09a8228cb13616cfc4f6e08454d26671fff4eab163341500`
- **Scrolls:** 22 (label-`22027` list; mirrored in [`registry-list.json`](registry-list.json))
- **Previous Version:** V5 mint tx `9a70d337327191b48312de790ab2639ef7fe789d2869a04bb31406b47806c1ab` (alive, superseded; V2–V4 burned)
- **Front door:** `$beacn` — the handle and the head share a wallet
- **Site:** `index.html` `REGISTRY_PTR` = the bare library policy id; the reader auto-selects the highest-`Version` head, so a new mint needs no redeploy.

Append-only: every head names its predecessor (`Previous Version` /
`Supersedes`), back through the burned V2–V4 mints to the retired datum head
`af5ee28d770a1f4bf6c252d79944a5fa2a7446fa2e6ef558707e238d881ec483#0`.
These files mirror on-chain state — regenerate them from chain, never hand-edit.
