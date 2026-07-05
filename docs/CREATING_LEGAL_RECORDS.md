# Create a Transaction-Backed Legal Record

This guide creates a numbered legal docket that the
[Ledger Scrolls Legal reader](https://beacnpool.github.io/ledger-scrolls/the Main Viewer (#s=legal-0001))
can discover from a policy ID.

The design has two layers:

1. **Document storage:** a Chain Scroll stores the exact document bytes in
   metadata page transactions and anchors their ordered hashes in a locked
   manifest UTxO.
2. **Docket record:** a native asset such as `LEGAL_0001` is minted under a
   signature policy. Its CIP-25 metadata points to the manifest and records
   the document hash. The policy signature authorizes the docket entry.

The blockchain proves key authorization, byte integrity, and time of record.
It does not by itself prove the civil identity of the key holder or guarantee
legal effect in every jurisdiction.

## 1. Requirements

- Linux shell, Python 3, `jq`, and a Conway-compatible `cardano-cli`
- A synced Cardano node and `CARDANO_NODE_SOCKET_PATH`
- A funded payment address, verification key, and signing key
- Enough ADA for every page transaction, the manifest UTxO, and the docket
  token transaction

Run the entire process on Preview testnet first. The included
`tools/lschain/mint.sh` currently targets mainnet; copy it and change
`NETWORK="--mainnet"` to the appropriate testnet network argument for a
rehearsal.

Never publish confidential agreements, personal data, private keys, passwords,
or material that may require deletion. On-chain bytes are public and permanent.
For confidential agreements, publish only an agreed hash and a non-sensitive
proof document.

## 2. Prepare the document

Use a self-contained file. HTML must contain its CSS and images and must not
depend on JavaScript, external fonts, CDNs, or remote URLs.

```bash
FILE=agreement.html
WORK=work/legal-0002

sha256sum "$FILE"
python3 tools/lschain/prepare.py "$FILE" \
  --content-type text/html \
  --codec auto \
  --out "$WORK"

jq . "$WORK/plan.json"
```

`plan.json` is the pre-publication receipt. Review:

- `sha256Decoded`: hash of the original document
- `sha256Encoded`: hash of the stored byte stream
- `codec`: `gzip` or `none`
- `pages`: number of on-chain page transactions

Do not proceed if the hashes or page count are unexpected.

## 3. Publish the Chain Scroll document

Select a dedicated pure-ADA UTxO. Passing it explicitly avoids accidentally
spending a registry head, NFT-bearing output, or another important UTxO.

```bash
export CARDANO_NODE_SOCKET_PATH=/path/to/node.socket

cardano-cli latest query utxo \
  --address "$(cat payment.addr)" \
  --mainnet \
  --socket-path "$CARDANO_NODE_SOCKET_PATH" \
  --output-json > "$WORK/available-utxos.json"

jq . "$WORK/available-utxos.json"

ROOT_TXIN='<tx-hash>#<index>'

tools/lschain/mint.sh \
  "$WORK" \
  payment.skey \
  payment.addr \
  "" \
  "$ROOT_TXIN"
```

The writer submits one metadata transaction per page, creates the manifest,
locks it at the always-fail script address, and writes `receipts.json`.

```bash
jq . "$WORK/receipts.json"

MANIFEST_TX=$(jq -r '.pointer.txHash' "$WORK/receipts.json")
MANIFEST_IX=$(jq -r '.pointer.txIx' "$WORK/receipts.json")
MANIFEST_TXIN="${MANIFEST_TX}#${MANIFEST_IX}"
DECODED_SHA=$(jq -r '.plan.sha256Decoded' "$WORK/receipts.json")
```

## 4. Create the docket signing policy

A docket is a native minting policy controlled by a signing key. Keep this
key stable: every future docket record must mint under the same policy.

For a simple single-signature docket:

```bash
mkdir -p docket

cardano-cli latest address key-hash \
  --payment-verification-key-file payment.vkey \
  > docket/signer.keyhash

SIGNER_KEY_HASH=$(cat docket/signer.keyhash)

jq -n --arg keyHash "$SIGNER_KEY_HASH" \
  '{type:"all",scripts:[{type:"sig",keyHash:$keyHash}]}' \
  > docket/policy.script

POLICY_ID=$(cardano-cli latest transaction policyid \
  --script-file docket/policy.script)

printf '%s\n' "$POLICY_ID" > docket/policy.id
```

For organizational records, use a reviewed multisignature or time-bounded
native script instead of blindly copying the single-key example. The reader
can discover the records either way, but the policy determines who is
authorized to create them.

## 5. Build the docket metadata

Choose the next permanent document number. Numbers are convention, not an
automatic counter: check the policy in the reader and on-chain before minting.
Never reuse a number.

```bash
DOC_NO=2
ASSET_NAME=$(printf 'LEGAL_%04d' "$DOC_NO")
ASSET_HEX=$(printf '%s' "$ASSET_NAME" | xxd -p -c 256)
TITLE='Example Agreement'
```

Create the CIP-25 metadata that connects the docket token to the Chain Scroll
manifest:

```bash
jq -n \
  --arg policy "$POLICY_ID" \
  --arg asset "$ASSET_NAME" \
  --arg title "$TITLE" \
  --argjson doc "$DOC_NO" \
  --arg txHash "$MANIFEST_TX" \
  --argjson txIx "$MANIFEST_IX" \
  --arg sha256 "$DECODED_SHA" \
  --arg signerKeyHash "$SIGNER_KEY_HASH" \
  '{
    "721": {
      ($policy): {
        ($asset): {
          name: $title,
          doc: $doc,
          mediaType: "text/html",
          sha256: $sha256,
          pointer: {
            kind: "manifest-chain-v2",
            txHash: $txHash,
            txIx: $txIx
          },
          signerKeyHash: $signerKeyHash
        }
      }
    }
  }' > "$WORK/docket-metadata.json"

jq . "$WORK/docket-metadata.json"
```

Required reader fields are:

- CIP-25 label `721`
- policy ID and asset-name keys
- `pointer.txHash` and `pointer.txIx`
- `sha256`
- `name`

`doc`, `mediaType`, and `signerKeyHash` are strongly recommended.

## 6. Mint the numbered docket token

Select a suitable UTxO from the funded signing address:

```bash
TXIN='<tx-hash>#<index>'
ADDR=$(cat payment.addr)

cardano-cli latest transaction build \
  --mainnet \
  --socket-path "$CARDANO_NODE_SOCKET_PATH" \
  --tx-in "$TXIN" \
  --mint "1 ${POLICY_ID}.${ASSET_HEX}" \
  --mint-script-file docket/policy.script \
  --metadata-json-file "$WORK/docket-metadata.json" \
  --change-address "$ADDR" \
  --out-file "$WORK/docket.raw"

cardano-cli latest transaction sign \
  --mainnet \
  --tx-body-file "$WORK/docket.raw" \
  --signing-key-file payment.skey \
  --out-file "$WORK/docket.signed"

cardano-cli latest transaction submit \
  --mainnet \
  --socket-path "$CARDANO_NODE_SOCKET_PATH" \
  --tx-file "$WORK/docket.signed"

DOCKET_TX=$(cardano-cli latest transaction txid \
  --tx-file "$WORK/docket.signed" | grep -oE '[0-9a-f]{64}' | head -1)

printf '%s\n' "$DOCKET_TX"
```

If the funding key and docket policy key are different, sign with both keys.
Do not claim the transaction is authorized by a key that did not satisfy the
actual minting policy.

## 7. Verify before publishing

Reconstruct the document independently:

```bash
cd koios-viewer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m lsview reconstruct-chain \
  --txin "$MANIFEST_TXIN" \
  --out /tmp/legal-record-check.html

sha256sum /tmp/legal-record-check.html
printf '%s  expected\n' "$DECODED_SHA"
```

Then open the docket policy in the public reader:

```text
https://beacnpool.github.io/ledger-scrolls/the Main Viewer (#s=legal-0001)#policy=<POLICY_ID>
```

Confirm that it reports the expected:

- number of documents under the policy
- total on-chain page count
- document title and number
- manifest pointer
- recording transaction
- SHA-256 verification result

Do not announce the record until reconstruction and hashes pass.

## 8. Keep complete receipts

Archive together:

- exact source document
- `plan.json`
- page metadata files
- Chain Scroll `receipts.json`
- docket policy script and policy ID
- docket metadata JSON
- signed transaction body
- manifest txin and docket mint tx hash
- original and reconstructed SHA-256 values

Never commit signing keys. Store them only in an appropriate encrypted key
store with tested backups and recovery procedures.

## Live example

The BEACN demonstration docket currently contains exactly one on-chain record:

- Policy: `97d3659dec8c60f69464959ab2156c64d74408d8950fea109c4d95e4`
- Asset: `LEGAL_0001`
- Manifest: `ceced54b2bd462b1ed41864f2583309666010ce1fb96b9f3dc9968174d958bc9#0`
- Pages: `1`

`LEGAL_0002` is the next available example number, but it has not been minted
under this policy.
