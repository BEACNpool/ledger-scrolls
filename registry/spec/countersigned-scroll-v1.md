# Countersigned Scrolls v1 — on-chain acceptance of on-chain terms

Status: PROPOSED (v1, July 2026)

A **countersigned scroll** is an agreement whose *document* is a Ledger
Scroll and whose *signatures* are ordinary Cardano transactions. The scroll
fixes the exact bytes of the terms forever; each party then sends a small
transaction from their own wallet carrying an **acceptance record** that
names the scroll and its hash. The chain supplies what a signing platform
sells you — document integrity, signer keys, timestamps, and ordering —
with no platform left to go out of business, lose the audit trail, or
charge a renewal.

The trust property, precisely: an acceptance transaction proves that **the
holder of a spending key** endorsed **these exact bytes** at **this block
time**. Which human holds the key is established off-chain (see
*Identity binding*).

## The acceptance record (metadata label 22026)

Each accepting party submits one transaction — any transaction they sign,
a minimal self-send is the norm — carrying metadata:

```json
{ "22026": {
    "v": 1,
    "t": "<64-hex tx hash of the scroll pointer>",
    "i": 0,
    "h": "<64-hex sha256 of the DECODED document>",
    "r": "buyer",
    "n": ["Ada Lovelace"]
} }
```

| field | required | meaning |
|---|---|---|
| `v` | yes | record version, `1` |
| `t` | yes | pointer transaction hash (the scroll being accepted), bare hex, no `0x` |
| `i` | yes | pointer output index (integer) |
| `h` | yes | `sha256Decoded` of the document, bare hex, no `0x` |
| `r` | no | the signer's role in the agreement, ≤ 64 chars (`"partyA"`, `"lender"`, …) |
| `n` | no | display name / statement, as an array of strings ≤ 64 bytes each |

Encoding rules:

- `t` and `h` are **exactly 64 characters of bare lowercase hex** — no `0x`
  prefix. This keeps every string within the ledger's 64-byte metadata
  string limit, so the record can be pasted into any wallet's metadata box
  as plain JSON (Eternl et al.) or built with `cardano-cli` — it is valid
  whether the wallet stores strings as text or bytes. Readers MUST accept
  both text and byte-string forms and normalize.
- Readers MUST tolerate unknown extra fields (forward compatibility) and
  MUST ignore records whose `v` they do not understand.

## Verification procedure (what a conforming reader proves)

Given a scroll pointer `T#I`:

1. Resolve and verify the scroll exactly as usual (manifest or Standard
   Scroll; hash-verified or nothing). Record its `sha256Decoded`.
2. Find acceptance transactions. Discovery is out of scope for v1 — the
   parties keep their acceptance tx hashes as receipts, exactly as minters
   keep scroll pointers. (Indexers *can* search label 22026, but the
   protocol never depends on search.)
3. For each acceptance tx: fetch it, take metadata label 22026, and check
   `t == T`, `i == I`, and `h == sha256Decoded` **computed from the
   reconstructed document, not from the manifest's claim**.
4. Attribute the acceptance: the endorsing credentials are the **payment
   credentials of the transaction's inputs** — the keys that had to sign
   for the transaction to exist. Display the input addresses (or their
   payment key hashes) and the block time.
5. An acceptance is valid only if steps 3–4 all hold. `r`/`n` are display
   metadata, never evidence — the evidence is the signature, the hash, and
   the block.

Result, in one sentence: *these keys endorsed these exact bytes at these
times, in this order* — reconstructible forever from any Cardano node.

## Identity binding (read this before relying on it)

A key is not a person. The chain proves a **wallet** accepted the bytes;
tying the wallet to a human is done the same way the address was trusted
for payment in the first place, and SHOULD be done **inside the document**:
put each party's name *and* the address they will accept from in the terms
themselves. Then the countersignature closes the loop — the named address
endorsed the document that names it. Exchanging addresses in the same
email/message thread as the deal, or using a long-held public identity
(an ADA Handle, a known donation address) strengthens the bond further.

This is an **evidence layer, not a legal system**. Electronic-signature
law is broad, but what a court admits is the court's call. What the chain
removes is every dispute about *which version* was signed and *when* —
the two arguments most agreements die on.

## Notes & non-goals

- **Withdrawal/amendment:** signatures cannot be unsigned; immutability is
  the product. Parties amend the way contract law always has — new terms,
  new scroll, new acceptances. A document can state "the latest commonly
  accepted version supersedes prior versions" in its own text.
- **Money:** countersigned scrolls hold the *meaning*, never the stake.
  Escrow is a smart contract's job. Code can hold the money; scrolls hold
  the meaning.
- **Bets:** the demo everyone understands, and legally unenforceable in
  many places. The serious wedge is agreements too small for lawyers:
  freelance scope and milestone acceptance, IOUs and family loans,
  co-founder splits before incorporation, private-party vehicle sales,
  landlord/tenant condition reports. The premium isn't competing with
  legal fees — it's competing with having no proof at all.

## Worked example (cardano-cli)

```bash
# terms.txt already minted as a scroll at $PTR (txhash#0), sha256 $H
cat > accept.json <<EOF
{ "22026": { "v":1, "t":"${PTR%#*}", "i":0, "h":"$H", "r":"partyB" } }
EOF
cardano-cli conway transaction build --mainnet \
  --tx-in <A_PURE_ADA_UTXO> \
  --tx-out "$(cat my.addr)+1500000" \
  --metadata-json-file accept.json \
  --change-address "$(cat my.addr)" --out-file tx.raw
# sign, submit, and KEEP THE TX HASH — that is your countersignature receipt.
```

Wallet route: the [Mint a Scroll](../../calculator.html) builder emits this
JSON pre-filled after a mint — paste it into your wallet's send-metadata
box, exactly like Chain-Scroll pages.
