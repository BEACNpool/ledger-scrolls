# Legacy Scroll Template

This template provides guidance for minting a Legacy Scroll (LS-PAGES v1) for large documents.

> **Note:** Legacy Scroll tooling is still in development. The process below describes the manual approach. Automated scripts are planned for a future release.

## Planned Files (Coming Soon)

- `policy-template.script` — Time-locked policy template
- `metadata-template.json` — CIP-25 metadata template

## Manual Process Overview

```bash
# 1. Compress your document
gzip -k large-document.pdf

# 2. Split into ~14KB chunks (CIP-25 metadata limit)
split -b 14000 large-document.pdf.gz page_

# 3. Convert each chunk to hex
for f in page_*; do xxd -p "$f" | tr -d '\n' > "$f.hex"; done

# 4. Create time-locked policy
# 5. Mint each page as CIP-25 NFT
# 6. Mint manifest NFT pointing to all pages
```

For a complete working example, see `docs/LEGACY_SCROLLS.md`.

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
