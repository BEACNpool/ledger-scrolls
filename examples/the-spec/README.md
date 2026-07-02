# The Spec — the protocol, stored in its own format

On July 2, 2026 the Chain Scroll wire specification
([`registry/spec/manifest-chain-v2.md`](../../registry/spec/manifest-chain-v2.md))
was minted on Cardano mainnet **as a Chain Scroll**. The chain now carries
its own law next to its own reader: a stranger with nothing but a Cardano
node can extract the specification, implement it, extract the reader, and
verify one against the other — no repository, no website, no us.

| Field | Value |
|---|---|
| Pointer | `manifest-chain-v2` · `e4845deed98471b29b35689cfdb76f18add189c8d8f5c61b2ef32ea7ce6d5cf9#0` |
| Content | `text/markdown`, gzip, 5,518 → 2,694 bytes, 1 page |
| SHA-256 (decoded) | `4793c38349cca60d552c52d68dfd950f3dd945db55c8a6a87f05ca6d98e3b242` |

```bash
cd koios-viewer
python3 -m lsview reconstruct-chain \
  --txin e4845deed98471b29b35689cfdb76f18add189c8d8f5c61b2ef32ea7ce6d5cf9#0 \
  --out spec-from-chain.md
sha256sum spec-from-chain.md   # 4793c383…b242
```

The repo copy of the spec is now hash-pinned to the chain: editorial
changes belong in a *new* spec version minted as a new scroll.
