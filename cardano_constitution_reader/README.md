````md
# Cardano Constitution Reader (On-Chain, Verified)

This tool reconstructs the Cardano Constitution directly from **on-chain NFT page payloads** (CIP-721 metadata) via **Blockfrost**, then verifies integrity with **SHA-256**.

It supports two modes:

- **Fast mode (recommended):** uses a saved *mint manifest* (`constitution_epoch_XXX_mints.json`) so it can fetch the exact mint TXs for each page (fewer API calls, less “it froze” anxiety).
- **Legacy mode:** scans the entire policy and discovers page mints automatically (more API calls, slower on free tier).

---

## What it fetches

### ✅ Constitution — Epoch 608 (current)

- **Policy ID:** `ef91a425ef57d92db614085ef03718407fb293cb4b770bc6e03f9750`
- **Manifest asset name:** `CONSTITUTION_E608_MANIFEST`
- **Manifest mint TX:** `2bad7fbe85f75efbc5f67138d824c785d1ad030c1e5fded094e74ca02f484653`
- **Pages:** 11 (`PAGE001` → `PAGE011`)
- **Codec:** gzip
- **SHA256 (original):** `98a29aec8664b62912c1c0355ebae1401b7c0e53d632e8f05479e7821935abf1`

**Page mint TXs (E608):**
- PAGE001: `eaf0f9bafd24cacd4f965e3b153853eb384cf55e1fe8c541f0d6382f33430fd1`
- PAGE002: `72cecb7d8daa6add86f7a77e681f05a6fc1871167e506b3bae4646cfec0bf651`
- PAGE003: `b3bf2add31d099102a899d028d9e261ef84b762d0e324efcc45ac08bffc547e3`
- PAGE004: `bcf447ac3161163146bc8aa29a3fde516e6c78442d171d6cdbf3a4e4530124c4`
- PAGE005: `ebb83944498c45339e62add37e38d93a5f31f45fe19bdefddf8e63cf848697b3`
- PAGE006: `18cd9fa7dd525da9bed21af6f21594ae72683aa882254615bcbbac97846b251b`
- PAGE007: `c1a98a192c178242f5160865221156fe21347ee6b7e6edbe70dc980c99eaf730`
- PAGE008: `edfc6688f37d07049e8e453cfe6d06e4a6821da8f68458e63a9b88a8887ecbdb`
- PAGE009: `84a4fea1e0178d02f32bed15e6f530841dbcf3666a107b3fc870e6b8ba009189`
- PAGE010: `bc0deeb3f991018785ba8d197364cb080e2df7bfa2828d3c6843b89b65d07010`
- PAGE011: `6397ecc3f0a0a8e3a3cb35096a9f7e75f15d4acf52ff6da5647247b18f62546f`

---

### ✅ Constitution — Epoch 541 (earlier ratification)

- **Policy ID:** `d7559bbfa87f53674570fd01f564687c2954503b510ead009148a31d`
- **Manifest asset name:** `CONSTITUTION_E541_MANIFEST`
- **Manifest mint TX:** `2e9c9e9fac7175839ea37d45b1f0123b4cebb3a92a6f2fa38f009a791e2b2a10`
- **Pages:** 7 (`PAGE001` → `PAGE007`)
- **Codec:** gzip
- **SHA256 (original):** `1939c1627e49b5267114cbdb195d4ac417e545544ba6dcb47e03c679439e9566`

**Page mint TXs (E541):**
- PAGE001: `d48ec5ec386c81a4ddcc2fa0be4f80514d764cf70630f19f80492a0e653df1e1`
- PAGE002: `f131f4fa23bb7c0db25c8afedce378fa6bf2e42600edc6b4bce264856eb0adeb`
- PAGE003: `87ed56db089e405264ee6dde6ee3bd169939569e6eb0461cc82ad88e6dd19fa4`
- PAGE004: `8be28125d95ec4f0b64cb4122dcb1d595c7132b369e14856ca3af429745e34c6`
- PAGE005: `5f1040210fbe19b485ffc88c106accb59a402ff36dbeff9b152a295cf221733d`
- PAGE006: `b654e1a89e083b26c09a0fd71c22e9a3af4bdca4c1bb9c78a8abc051184149ab`
- PAGE007: `6cc9352bc5ae09cf13196f0b37454b5c2b5510bf4ba358ddca28c072a500fb0a`

---

## Prereqs

- Python 3 (`python3 --version`)
- Internet access
- A **Blockfrost Cardano Mainnet** API key (starts with `mainnet...`)
  - Free tier is typically sufficient (this script rate-limits and retries).

---

## Quick start (recommended)

```bash
git clone https://github.com/BEACNpool/ledger-scrolls.git
cd ledger-scrolls/cardano_constitution_reader

# Run (prompts for Blockfrost key + epoch 541/608)
python3 cardano_constitution_reader.py
````

---

## Quick start (no prompts)

### Linux / macOS / WSL

```bash
git clone https://github.com/BEACNpool/ledger-scrolls.git
cd ledger-scrolls/cardano_constitution_reader

export BLOCKFROST_PROJECT_ID="mainnet_...yourkey..."
python3 cardano_constitution_reader.py --epoch 608 --non-interactive
```

### Windows PowerShell

```powershell
git clone https://github.com/BEACNpool/ledger-scrolls.git
cd ledger-scrolls\cardano_constitution_reader

$env:BLOCKFROST_PROJECT_ID="mainnet_...yourkey..."
python cardano_constitution_reader.py --epoch 608 --non-interactive
```

---

## Fast mode (recommended)

If `constitution_epoch_541_mints.json` and/or `constitution_epoch_608_mints.json` exists in the same folder as the reader,
the script **auto-detects and uses it**.

You can also explicitly pass a file:

```bash
python3 cardano_constitution_reader.py --epoch 608 --mints-file constitution_epoch_608_mints.json
```

Fast mode is less likely to “feel stuck” because it hits **known mint TXs** directly instead of scanning every asset under the policy.

---

## Output

The script writes a file like:

* `Cardano_Constitution_Epoch_608.txt`
* `Cardano_Constitution_Epoch_541.txt`

…and prints the computed SHA-256 hash (must match the published expected hash to pass verification).

Tip (Linux):

```bash
xdg-open Cardano_Constitution_Epoch_608.txt
```

Tip (WSL → Windows Notepad):

```bash
notepad.exe "$(wslpath -w ./Cardano_Constitution_Epoch_608.txt)"
```

```
::contentReference[oaicite:0]{index=0}
```
