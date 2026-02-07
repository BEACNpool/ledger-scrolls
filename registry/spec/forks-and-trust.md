# Forks, Heads, and Trust

The chain contains *all* published heads (updates). There is no global "main".

## Heads are append-only

Updating a registry means publishing a **new head** pointing to a new registry list snapshot.

- old heads remain valid history
- no updates mutate old data

## Forks are a feature

Anyone can:

1. Read your head `H0`
2. Create a new head `H1` that references `H0` and a new list `L1`
3. Publish `H1` as their own "registry"

They cannot change `H0`. They can only publish their own head.

## Reader choice is the firewall

A viewer decides which heads to follow.

Examples:

- "BEACN Canonical": pinned to your head hash (or your signer key)
- "Community Fork": pinned to a different head hash

Spam forks exist, but they only matter if a reader opts into them.

## Trust anchors (v0 → v1)

v0: out-of-band trust anchors
- pinned head hash
- pinned policy id / asset

v1: signed heads
- introduce `signature` field in head objects
- publish signer keys in an on-chain or well-known location

## Governance (off-chain)

GitHub can host:

- naming conventions
- inclusion policy for canonical lists
- tooling and viewer reference implementations

But GitHub does not control on-chain forks; it only coordinates the canonical line.
