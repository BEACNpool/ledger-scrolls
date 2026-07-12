# Registry NFT (v2) — the on-chain catalog

**Status: normative, current.** This is the registry model the shipped readers
(`index.html`, `lsview registry-dump`) implement. It supersedes the v0
datum head/list model ([`format.md`](format.md) / [`resolution.md`](resolution.md))
for *catalog discovery*; the v0 documents remain normative for the entry and
pointer object shapes, which this spec reuses.

## The idea

The whole catalog is one NFT. A **Registry Head** is a native asset minted
under a publisher policy (the "library policy"); the scroll list rides in the
**mint transaction's metadata under label `22027`**. Because mint-tx metadata
is immutable, every version of the catalog is a permanent on-chain object —
updating the library means minting a new head with a higher `Version`, never
editing anything.

```
 library policy ──▶ Registry Head NFTs (V2, V3, … Vn)
                        │  721: Type="Registry Head", Version=n
                        ▼
                    mint tx metadata label 22027
                        │  { format, version, entries[] }
                        ▼
                    scroll pointers ──▶ verified bytes
```

There is no locked UTxO, no datum, and no spend-and-recreate step. The head
token itself can sit in any wallet (that is what makes the `$handle` front
door work, below).

## The Registry Head NFT (label `721`)

A Registry Head is a CIP-25 asset whose `721` metadata carries, in addition to
the usual `name` / `image` / `mediaType`:

| Trait | Required | Meaning |
|---|---|---|
| `Type` | MUST | The exact string `"Registry Head"`. This is how readers tell heads apart from every other asset under the policy. |
| `Version` | MUST | Integer (may be a decimal string). Readers select the head with the **highest numeric Version**. |
| `Previous Version` | SHOULD | Mint tx hash of the head this one supersedes — the lineage chain. (The first heads used `Supersedes`; readers do not need either field to resolve.) |
| `Ledger Scrolls Pointer` | SHOULD | The paste-able resolution key `<policyId>.<ASSET_NAME>`, so the NFT itself tells a human how to open it. |
| `Library`, `Channel`, `Scrolls`, `Network`, `Reader`, `Minted` | MAY | Human-facing catalog card fields. |

A head whose mint tx does **not** carry a label-`22027` list is not a
Registry Head, whatever its `Type` says — readers MUST require both.

## The scroll list (label `22027`)

The mint transaction's metadata label `22027` holds the catalog:

```json
{
  "format": "ledger-scrolls-registry-list",
  "version": 2,
  "entries": [
    { "n": "beacn-leaks-000", "k": "manifest-chain-v2",
      "t": "f3ee01c1e742c27c205867de4cfa8836e4ab541b9da0d5652aa4d269c73255c7", "i": 0 },
    { "n": "bible", "k": "cip25-pages-v1",
      "p": "2f0c8b54ef86ffcdd95ba87360ca5b485a8da4f085ded7988afc77e0",
      "a": "BIBLE_MANIFEST" }
  ]
}
```

- `format` — MUST be `"ledger-scrolls-registry-list"`.
- `version` — the **list-format** version (currently `2`). This is not the
  head's `Version`; a V6 head still carries a version-2 list.
- `entries[]` — compact entries. Keys are single letters because tx-metadata
  strings cap at 64 bytes and every byte of the list is paid for:

| Key | Meaning | Used by |
|---|---|---|
| `n` | name — `^[a-z0-9-]{1,64}$` (v0 name rules) | all kinds |
| `k` | pointer kind — `manifest-chain-v2`, `utxo-inline-datum-bytes-v1`, or `cip25-pages-v1` | all kinds |
| `t` | 64-hex tx hash | txin kinds |
| `i` | output index (integer; readers default a missing `i` to `0`) | txin kinds |
| `p` | 56-hex policy id | `cip25-pages-v1` |
| `a` | manifest asset name (ASCII) | `cip25-pages-v1` |

Readers expand each compact entry to the long-form
`{ name, pointer: { kind, txHash, txIx } }` /
`{ name, pointer: { kind, policyId, manifestAsset } }` shape defined in
[`format.md`](format.md); everything downstream (fetch, hash verification,
render) is unchanged from v0. Anything else a reader wants to show for an
entry (content type, size, SHA-256) it reads from the scroll's own manifest —
the list stays a pure name→pointer map.

## Resolution — what a reader accepts

A conforming reader accepts four registry inputs (a fifth is optional):

### 1. Bare policy id (56 hex) — "open the latest catalog"

1. List the policy's assets (Koios `policy_asset_list`). Burned assets stay
   listed (supply 0) and their mint metadata stays readable — burning does not
   unpublish a catalog version.
2. (Optimization, not semantics: pre-filter to asset names containing
   `REGISTRY`; fall back to all assets if none match.)
3. Fetch `asset_info` for the candidates; keep assets whose `721` metadata has
   `Type == "Registry Head"` **and** whose mint tx metadata carries label
   `22027`.
4. Select the head with the highest numeric `Version`. Its `22027` list is
   the catalog.

### 2. `policy.ASSET` — "pin one version"

Fetch `asset_info` for exactly that asset; its mint tx's label-`22027` list is
the catalog. The asset-name half may be ASCII or hex (readers try hex if the
string is even-length hex ≤64 chars, else hex-encode the ASCII). Pinning a
superseded — even burned — head is valid forever: mint metadata is immutable.

### 3. `$handle` — the human front door

An [ADA Handle](https://adahandle.com) resolves to a wallet; the wallet's
newest Registry Head is the catalog:

1. Handle policy `f0ff48bbb7bbe9d59a40f1ce90e9e9d0ff5002ec48f232b49ca0fb9a`.
   Try the CIP-68 user token first (asset name `000de140` + hex of the handle,
   lowercase, no `$`), then the legacy plain hex name.
2. `asset_addresses` → the holder's **stake address**.
3. `account_assets` for that stake address → candidate assets whose ASCII name
   contains `REGISTRY`.
4. Apply the same head filter and highest-`Version` selection as input 1
   (candidates may span multiple policies here — the wallet, not the policy,
   is the trust anchor).

**Same-wallet rule:** the handle and a Registry Head NFT must sit in the same
wallet (same stake key). Move either one and the `$handle` door stops
resolving — the pinned and bare-policy inputs are unaffected.

### 4. 64-hex tx hash — "read a mint tx directly"

Fetch the transaction's metadata (`tx_metadata`); its label-`22027` list is
the catalog. This works for any head's mint tx, current or superseded.

### 5. CIP-14 `asset1…` fingerprint (OPTIONAL)

Readers MAY accept an asset fingerprint (what pool.pm displays), resolve it to
`policy.ASSET`, and continue as input 2.

In every case: if the resolved metadata has no label-`22027` list, resolution
MUST fail — never silently fall back to a different catalog.

## Publishing and updating

- **Publish:** mint a Registry Head under your policy with `Type`,
  `Version: 1`, and the label-`22027` list in the same transaction.
- **Update:** mint a new head with a **strictly higher** `Version` and the
  full new list (lists are snapshots, not diffs). Set `Previous Version` to
  the prior head's mint tx. Re-point nothing: bare-policy and `$handle`
  readers pick up the new head automatically.
- **Housekeeping:** burning superseded head tokens is optional. A burn removes
  the token from wallets (so it can't be pinned *by holding* or found via
  `$handle`) but the mint tx, its `721` traits, and its `22027` list remain
  on-chain and resolvable forever via inputs 2 and 4.
- **Forks:** unchanged from v0 — anyone can mint their own head under their
  own policy. Readers choose their trust anchor; there is no global root.

## The live deployment (the facts a stranger can check)

- Library policy: `8d6d38b3967028a15fc0e401b53c73a75ac654affc3f817c750c8b80`
  (the LEDGER_SCROLLS publisher channel).
- Public front door: **`$beacn`** (handle and current head share a wallet).
- Current head: `LS_REGISTRY_V6`, 22 scrolls, mint tx
  `955c6d2aa84b1d1d09a8228cb13616cfc4f6e08454d26671fff4eab163341500`.
- Lineage (each `Previous Version`/`Supersedes` links back):
  - V2 `d46d3729ecc04fce1995b7e1008ed690c8cd1cc502d45edcf19a73765b581bba` (17 scrolls) — **burned**
  - V3 `5dfff55abbed3b1a59782d6a27dc66eb6e4beeb9054f0057b4a3b79993c48057` (21) — **burned**
  - V4 `ab88b95af72e2c1752a205254b94ec8fd6237f3600b5c7ac1019f094242e1288` (21) — **burned**
  - V5 `9a70d337327191b48312de790ab2639ef7fe789d2869a04bb31406b47806c1ab` (21) — alive, superseded
  - V6 `955c6d2aa84b1d1d09a8228cb13616cfc4f6e08454d26671fff4eab163341500` (22) — **current**
  - (burn tx for V2–V4:
    `e15a409533e953c69309936f5f7111493ee3591f72e02b25a442cec796d71d6a`)
- Tracked mirror of the current list:
  [`registry/published/registry-list.json`](../published/registry-list.json)
  (regenerated from chain — never hand-edited).

## Lineage from the v0 datum registry

Before 2026-07-07 the catalog was a JSON head/list pair in locked UTxO datums
(the model `format.md`/`resolution.md` specify). Those heads are spent and the
line is retired; the last datum head was
`af5ee28d770a1f4bf6c252d79944a5fa2a7446fa2e6ef558707e238d881ec483#0` (17
scrolls), which `LS_REGISTRY_V2`'s `Supersedes` trait names — the lineage
crosses the model change without a gap. Readers that paste a datum-era head
txin get a "legacy registry" verdict from `index.html`; `lsview` still reads
them via `--legacy-head`.

## Reference implementations

- Browser: `index.html` — `resolveRegistry()` (all five inputs).
- Python: `koios-viewer/lsview` — `resolve_registry_nft()` /
  `lsview registry-dump` (bare policy; `--legacy-head` for datum-era heads).
