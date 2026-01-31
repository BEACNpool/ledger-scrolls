# Legacy Scroll Template

This template provides everything you need to mint a Legacy Scroll (LS-PAGES v1) for large documents.

## Files

- `policy-template.script` — Time-locked policy template
- `metadata-template.json` — CIP-25 metadata template
- `split-content.sh` — Script to split large files into pages
- `mint-pages.sh` — Script to mint all pages

## Quick Start

```bash
# 1. Copy this directory
cp -r templates/legacy-scroll my-document
cd my-document

# 2. Add your document
cp /path/to/large-document.pdf document.pdf

# 3. Compress (recommended)
gzip -k document.pdf

# 4. Split into pages
./split-content.sh document.pdf.gz

# 5. Create policy and mint
./mint-pages.sh /path/to/payment.skey /path/to/payment.addr
```

## Page Structure

Each page NFT contains:

```json
{
  "721": {
    "<policy_id>": {
      "DocumentPage0": {
        "name": "Document Page 0",
        "i": 0,
        "payload": [
          "hex_chunk_1",
          "hex_chunk_2",
          "..."
        ]
      }
    }
  }
}
```

## Important Notes

1. **Time-lock your policy** — Set a deadline after which no new pages can be minted
2. **Mint all pages before deadline** — Once expired, the document is final
3. **Keep sequential indices** — The `i` field must be 0, 1, 2, ...
4. **64-char hex chunks** — CIP-25 has string length limits

## Reconstruction

The viewer reconstructs by:
1. Querying all NFTs under the policy
2. Sorting by `i` index
3. Concatenating all payload chunks
4. Decompressing if needed
