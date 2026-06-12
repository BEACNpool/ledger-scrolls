# Publisher Channels v1 — unforgeable authorship feeds

Status: ACTIVE (first channel: BEACN Leaks, June 2026)

A **publisher channel** is a Cardano minting policy used as a permanent,
unforgeable byline. Each publication is one NFT minted under the policy
whose CIP-25 metadata carries a Ledger Scrolls pointer to the content.

The trust property: a policy ID is the hash of a policy script keyed to the
publisher's signing key. **Nobody can mint under a policy ID without the
key** — so anything appearing under the channel's policy ID is provably
from the publisher, with zero platform, registrar, or verifier involved.
Readers follow a policy ID the way they once followed a handle, except no
authority can suspend, reassign, or impersonate it.

## Channel policy

A simple signature script, deliberately **without a time lock** (the
channel stays open for future issues; content immutability comes from the
scrolls themselves, not the policy):

```json
{ "type": "sig", "keyHash": "<publisher key hash>" }
```

The policy ID is computable before anything is minted, so a publication can
declare its own channel in its content.

## Issue NFTs

Asset names: `<CHANNEL>_<NNNN>` (zero-padded). Label-721 metadata:

```json
{ "721": { "<policyId>": { "<CHANNEL>_<NNNN>": {
  "name": "<title>",
  "mediaType": "<MIME of the scroll>",
  "publisher": "<name>",
  "channel": "<channel name>",
  "issue": <int>,
  "pointer": { "kind": "manifest-chain-v2", "txHash": "<64-hex>", "txIx": 0 },
  "sha256": "<64-hex of the decoded scroll bytes>",
  "description": ["<lines of <=64 bytes>"]
}}}}
```

`pointer` MAY be any canonical pointer kind; `sha256` MUST match the scroll
entry so a reader can verify content without trusting the channel mint.

## Following a channel

One keyless query lists everything ever published:

```bash
curl -X POST https://api.koios.rest/api/v1/policy_asset_list \
  -H 'Content-Type: application/json' \
  -d '{"_asset_policy":"<policyId>"}'
```

Then `asset_info` per asset yields the minting metadata with the pointer.
Resolution and verification of the content follow the pointer's own spec.

## Caveats (state them, never hide them)

- A channel proves *key custody*, not legal identity. Key theft = channel
  theft; publishers should plan rotation (mint a signed "successor channel"
  notice as a final issue).
- The channel NFT itself is wallet-held and movable; the *mint record* is
  what proves authorship, not current custody of the token.
- Burning an issue NFT does not unpublish anything: the mint metadata and
  the scroll are immutable history.

## Live channels

| Channel | Policy ID | First issue |
|---|---|---|
| BEACN Leaks | `5f569d01614c42003131c40b46d0b58c351a718907645c96d6da5415` | `BEACN_LEAKS_0000` — Issue 000: The Manifesto (`examples/beacn-leaks-000/`) |
