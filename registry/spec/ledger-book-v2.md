# Ledger Book v2 — unique transferable on-chain guestbooks

Status: ACTIVE FOR NEW MINTS · v1 signatures remain readable · License: MIT

Version 2 tightens the NFT identity and supply rules without changing metadata
label `22031` or invalidating existing `ledger-book-v1` entries.

## Canonical identity

A book key is the exact Cardano asset id, encoded as two metadata strings:

```json
"k": ["<56-hex policy id>", "<0-64 hex asset-name bytes>"]
```

Readers MUST compare policy and asset-name bytes, not a decoded display name.
For compatibility, readers SHOULD also accept the v1 ASCII asset-name form and
the documented 64-byte prefix form.

## Mint policy

A v2 Book NFT MUST:

1. Mint exactly one unit.
2. Use an `all` native script containing both the minter payment-key signature
   and a `before` slot condition.
3. Include that same slot as the transaction upper validity bound.
4. Carry CIP-25 `Type: "Ledger Book"`, `protocol: "ledger-book-v2"`, and
   `mintBeforeSlot` metadata.

Once the slot passes, the policy can neither mint another copy nor burn the
existing book. Readers MUST require current total supply exactly one. A reader
that cannot inspect the mint policy MUST label the time-lock check unverified;
metadata alone is a claim, not proof of the policy bytes.

## Complete history

Readers reconstruct every address that held the asset and then collect every
matching `22031` entry. Implementations MAY impose resource ceilings, but MUST
surface `partial` rather than presenting a truncated result as the complete
book. Provider page limits MUST be detected or paginated.

## Signature validity

In addition to the v1 metadata envelope, a conforming entry MUST contain an
output paying a protocol-valid minimum-UTxO anchor to the keeper at the entry's
block. Readers SHOULD report separately:

- metadata validity;
- book-key match;
- anchor payment validity;
- sender/input attribution; and
- ownership-history completeness.

These are separate facts. Missing provider data is `unknown`, never silently
treated as valid or invalid.

