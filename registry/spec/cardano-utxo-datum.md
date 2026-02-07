# Cardano UTxO Inline Datum Encoding (Registry v0)

This registry uses **UTxO inline datum** as a transport for small registry objects (e.g., the Registry Head and small Registry Lists).

## Why this exists

`cardano-cli` (ScriptData) enforces a constraint that a single ByteString chunk must be <= 64 bytes when serializing datum as raw bytes.

To store arbitrary-length UTF-8 JSON bytes inside datum while keeping decoding simple, we encode datum as:

- **CBOR indefinite-length byte string** whose chunks are each <= 64 bytes
- The concatenated bytes are **UTF-8 JSON**

This is still CBOR type "byte string" and will decode to a single `bytes` value in standard CBOR decoders.

## Encoding

Datum CBOR should be:

- `0x5f` (start indefinite byte string)
- repeated chunks: `0x40..0x58 <len> <bytes>` (each chunk <= 64 bytes)
- `0xff` (break)

The concatenated payload bytes MUST be valid UTF-8 JSON.

## Decoding

1) Read inline datum CBOR bytes from the UTxO.
2) CBOR-decode it to a `bytes` value.
3) UTF-8 decode to text.
4) Parse JSON to object.

## Pointer kind for datum-bytes

For the Registry standard, the pointer kind is:

- `utxo-inline-datum-bytes-v1`
  - `txHash`: 64-hex transaction id
  - `txIx`: integer output index

A viewer may optionally resolve the containing block point via Blockfrost/Koios or via local node/indexer.
