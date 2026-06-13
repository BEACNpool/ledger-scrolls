# LEGAL-0001 — Declaration of Authorship and Proof of Existence

The legal-records use case: a formal instrument recorded on Cardano whose
**execution is the Ed25519 signature on its recording transaction** (only
the docket key could mint `LEGAL_0001`), whose **date of record is the
block time** (a postmark no party controls), and whose **integrity is its
SHA-256 seal** (recomputed by every reader). The document itself explains
this theory in six articles — including the honest limits (key custody ≠
legal identity; jurisdictional variance; record only the *hash* of
confidential agreements).

| Field | Value |
|---|---|
| Document | `LEGAL-0001` in the BEACN Ledger Docket |
| Docket policy | `97d3659dec8c60f69464959ab2156c64d74408d8950fea109c4d95e4` |
| Recording tx (the execution) | `ad23968e473b25fc1c226a49d6eafe5b343376a1c2430977877584a7af43bbf8` |
| Instrument pointer | `manifest-chain-v2` · `ceced54b2bd462b1ed41864f2583309666010ce1fb96b9f3dc9968174d958bc9#0` |
| Seal (SHA-256) | `8c95db4bb4248d82d3d5c4bb49dfe0200d779f4b6905cd3b5649fcb847378bc1` |

Open the docket policy in the public reader:
**[`legal.html#policy=97d365…d95e4`](https://beacnpool.github.io/ledger-scrolls/legal.html#policy=97d3659dec8c60f69464959ab2156c64d74408d8950fea109c4d95e4)** —
which inventories the policy, reports its on-chain document/page counts,
compiles a Certificate of Record, and renders the instrument only after the
seal verifies.

To create another compatible legal record, follow
**[Creating a Transaction-Backed Legal Record](../../docs/CREATING_LEGAL_RECORDS.md)**.

`legal-0001-declaration.html` is the exact recorded source; `receipts.json`
holds every transaction hash.
