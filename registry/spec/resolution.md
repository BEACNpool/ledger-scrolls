# Resolution & Verification

Goal: **Name → Pointer → Verified Bytes**

## Resolution algorithm (v0)

Given:

- a trusted **head** (or a trusted registry list)
- a target `name`

Steps:

1. **Obtain the registry list bytes** referenced by the head (`head.registryList`).
2. **Parse** the registry list object and locate `entries[]` item where `entry.name == name`.
3. From the entry, read:
   - `pointer`
   - `contentType`
   - `sha256`
4. **Fetch bytes** using `pointer.kind` rules.
5. **Verify**:
   - compute SHA-256 of fetched bytes
   - compare to `entry.sha256`
6. If valid, the viewer may render/store the bytes as `entry.contentType`.

## What is “trusted”?

Trust is explicit and reader-controlled.

A viewer can trust:

- a specific head hash (pinned)
- a policy id / asset that is considered authoritative
- a signature scheme over head objects (future)

## Failure modes

- Pointer fetch fails → unresolved name.
- Hash mismatch → bytes are untrusted; do not render as canonical.
- Multiple entries with same name → v0: viewer SHOULD take the **first** occurrence and warn.

## Caching

Because verification is hash-based, viewers can aggressively cache content by `sha256`.
