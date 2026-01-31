# Security Policy

## 🔐 Security Model

Ledger Scrolls operates on a **trustless security model**:

- **No server** — Everything runs client-side in your browser
- **No accounts** — No registration, no passwords, no data collection
- **No custody** — Your keys never leave your machine
- **Verification** — All content can be verified via SHA256 hashes

## ⚠️ Important Considerations

### Content is Public

**Everything you inscribe is visible to everyone, forever.**

- Don't inscribe private information
- Don't inscribe credentials or secrets
- Don't inscribe personal data you wouldn't want public

### Permanence is Real

**There is no undo button.**

- Once minted, content cannot be deleted
- Once locked, ADA cannot be recovered
- Verify content thoroughly before minting

### API Keys

If you use Blockfrost:

- API keys are stored in `localStorage`
- Keys are only sent to Blockfrost's servers
- Clear browser data to remove stored keys
- Consider using read-only project IDs

## 🛡️ Viewer Security

### Content Sandboxing

HTML scrolls render in sandboxed iframes:

```javascript
sandbox="allow-same-origin"
```

This prevents:
- Script execution
- Form submissions
- Popup windows
- Navigation to other pages

### Hash Verification

Always verify important documents:

1. Download the original
2. Calculate SHA256: `sha256sum document.pdf`
3. Compare with the on-chain hash
4. Match = authentic, unmodified content

## 🔍 Auditing Scrolls

Before trusting a scroll's content:

1. **Verify the TX** — Check it exists on cardanoscan.io
2. **Verify the hash** — Compare SHA256 hashes
3. **Check the lock** — Confirm it's at the always-fail address
4. **Review the source** — Who minted it? When?

## 🚨 Reporting Vulnerabilities

If you discover a security vulnerability:

1. **Do not** open a public issue
2. **Email** security concerns privately
3. **Include** detailed reproduction steps
4. **Wait** for acknowledgment before disclosure

Contact: Open a private security advisory on GitHub

## ✅ Best Practices

### For Minting

- [ ] Test on testnet first
- [ ] Verify content before minting
- [ ] Double-check addresses
- [ ] Keep your signing keys secure
- [ ] Review transaction details before signing

### For Viewing

- [ ] Use the official repository
- [ ] Verify hashes for important documents
- [ ] Don't trust unverified scrolls blindly
- [ ] Check the source of shared viewer links

### For Development

- [ ] Review all dependencies
- [ ] Don't add unnecessary libraries
- [ ] Keep the codebase auditable
- [ ] Document security-relevant code

## 📋 Dependency Security

The viewer uses minimal dependencies:

| Library | Purpose | Risk |
|---------|---------|------|
| pako.min.js | Gzip decompression | Low (pure JS, well-audited) |
| cbor.min.js | CBOR decoding | Low (pure JS) |

No npm, no build system, no supply chain complexity.

## 🔗 External Services

### Blockfrost

- Purpose: Blockchain queries
- Data sent: Query requests (addresses, transactions)
- Data stored: Nothing (stateless queries)
- Trust level: Medium (third-party service)

### Koios

- Purpose: Blockchain queries (alternative)
- Data sent: Query requests
- Data stored: Nothing
- Trust level: Medium (community-operated)

## 🏛️ Immutability Guarantees

| Component | Immutable? | Notes |
|-----------|------------|-------|
| On-chain content | ✅ Yes | Protected by Cardano consensus |
| Locked UTxOs | ✅ Yes | Always-fail script ensures permanence |
| Viewer code | ❌ No | Repository can be updated |
| External APIs | ❌ No | Services may change or disappear |

**The viewer is a convenience. The chain is the truth.**

---

*Security is a process, not a product. Stay vigilant.*
