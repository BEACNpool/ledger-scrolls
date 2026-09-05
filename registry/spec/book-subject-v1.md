# Optional Book subject, version 1

Status: implemented extension, synthetic wallet-tested; no acceptance mint made
for this extension in the 2026-09-05 rebuild.

A Book NFT carrying `protocol: "ledger-book-v2"` MAY include `subject` in the
asset's CIP-25 metadata. Existing readers ignore this optional field. The Book
native mint policy, identity, and entry envelope (`22031`) are unchanged.

```json
{
  "v": 1,
  "network": "mainnet",
  "tx": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "ix": 0,
  "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "title": "A preserved work"
}
```

The hashes above are illustrative placeholders, not an existing work.

- `v` MUST be integer `1`.
- `network` MUST be `mainnet` or `preview`. A CIP-30 network ID of zero in this
  application assumes Preview; Preprod is not supported.
- `tx` MUST be 64 lowercase hexadecimal characters naming the original locked
  datum or Chain Scroll manifest transaction.
- `ix` MUST be a safe nonnegative integer no greater than 65535.
- `sha256` MUST be 64 lowercase hexadecimal characters committing to the decoded
  original file bytes.
- `title` MUST be a UTF-8 string at most 64 bytes; an empty title is permitted.

The structure is encoded as a Cardano transaction-metadata map. Every text key
and value satisfies the 64-byte metadata-string limit. Unknown additional subject
keys SHOULD be ignored by readers, but the required fields MUST be validated.
Malformed subject metadata MUST NOT prevent reading otherwise valid historic
Book entries. It MUST be reported and MUST NOT produce a trusted attachment link.

A reader following `fromBook` MUST retrieve the named asset's own CIP-25 metadata,
check the Book type and subject fields, and require the link's network, pointer,
and fingerprint to match them. It then reconstructs the work using the existing
Scroll format, enforces declared sizes and hashes, and separately compares the
decoded fingerprint against `subject.sha256`. Mismatch MUST prevent rendering.

A subject entered into a creation form is an assertion by the minter. Format
validation is not proof that its file exists. The interface offers “Read and
check” before minting. Attaching someone else's work does not transfer copyright,
prove authorship, or endorse it. Guest entries remain entries, not countersigned
acceptance of the attached work.

Canonical new browser links use `?book=POLICY.0xASSET_NAME_HEX` to disambiguate
raw asset bytes from a legacy text name consisting only of hexadecimal characters.
Book signature identity continues to use the existing `[policy, rawNameHex]`
array. Legacy `policy.Name` links retain their existing interpretation.

The pointer and fingerprint live in the Book mint transaction. Browser saved
shelves, URL query strings, and cover previews are conveniences, never the
canonical attachment record.
