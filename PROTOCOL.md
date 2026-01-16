
# Ledger Scrolls Protocol

## Overview
Ledger Scrolls uses Cardano metadata labels to publish immutable data chunks. Registrations use a beacon pattern for discovery.

## Registration (Beacon)
- Label: 777
- Format: ["LS:Register", "Name:<scroll_name>", "PolicyID:<policy_id>", "StartSlot:<slot>", "Structure:<type>", "Description:<desc>"]
- Example: ["LS:Register", "Name:The Cardano Bible", "PolicyID:2f0c8b54...", "StartSlot:115000450", "Structure:Book/Text", "Description:The Holy Bible on Cardano"]

## Content Chunks
- Labels: 777 (custom), 674 (messages), 721 (NFTs)
- Structure: {"i": <index>, "payload": [{"bytes": "<hex_chunk>"}, ...]}
- Compressed as gzip hex segments across TXs.

## Reconstruction
Collect chunks by policy ID from start slot, sort by 'i', concat hex, decompress gzip to original (e.g., HTML).
