diff --git a/viewer.py b/viewer.py
index 1111111..2222222 100755
--- a/viewer.py
+++ b/viewer.py
@@ -1,6 +1,6 @@
 #!/usr/bin/env python3
 """
 Ledger Scrolls Viewer - Open Source Standard
@@
 import argparse
 import gzip
 import hashlib
 import json
 import os
 import re
 import sys
 import time
 from pathlib import Path
 from typing import Any, Dict, List, Optional, Tuple

 import requests

@@
 def sha256_hex(data: bytes) -> str:
     return hashlib.sha256(data).hexdigest()

 def hex_to_bytes(hex_str: str) -> bytes:
-    return bytes.fromhex(hex_str)
+    hs = (hex_str or "").strip()
+    if hs.startswith(("0x", "0X")):
+        hs = hs[2:]
+    # tolerate whitespace/newlines just in case
+    hs = re.sub(r"\s+", "", hs)
+    if hs == "":
+        return b""
+    return bytes.fromhex(hs)

 def hex_to_utf8(hex_str: str) -> str:
     try:
         return hex_to_bytes(hex_str).decode("utf-8")
     except Exception:
         return ""

 def safe_print(msg: str) -> None:
     print(msg, flush=True)

@@
 def payload_to_bytes(payload: Any) -> bytes:
     """
     Supports payload styles:
       1) Detailed schema list: [{"bytes":"ABCD..."}, {"bytes":"..."}]
-      2) Simple list: ["ABCD...", "...."]
+      2) Simple list: ["0xABCD...", "ABCD..."]
     """
     out = bytearray()
     if payload is None:
         return b""

     if not isinstance(payload, list):
         raise ValueError(f"payload is not a list (got {type(payload).__name__})")

     for item in payload:
-        if isinstance(item, dict) and "bytes" in item and isinstance(item["bytes"], str):
-            out.extend(hex_to_bytes(item["bytes"]))
+        if isinstance(item, dict) and "bytes" in item and isinstance(item["bytes"], str):
+            out.extend(hex_to_bytes(item["bytes"]))
         elif isinstance(item, str):
-            out.extend(hex_to_bytes(item))
+            out.extend(hex_to_bytes(item))
         else:
             raise ValueError(f"Unsupported payload element: {repr(item)[:120]}")
     return bytes(out)

@@
 def main() -> int:
     ap = argparse.ArgumentParser(description="Ledger Scrolls Viewer (Blockfrost, CIP-25/721)")
     ap.add_argument("--policy", default="", help="Policy ID (hex). If omitted, you’ll be prompted.")
     ap.add_argument("--blockfrost", default="", help="Blockfrost project_id (mainnet). Or set env BLOCKFROST_PROJECT_ID.")
     ap.add_argument("--out", default="", help="Output filename (default: ledger_scroll_<policy>.html or .bin)")
     ap.add_argument("--no-gunzip", action="store_true", help="Do not gunzip even if the bytes look like gzip")
+    ap.add_argument("--debug", action="store_true", help="Verbose debug output")
     args = ap.parse_args()

@@
         safe_print(f"\nManifest: {manifest_asset_name or '(unknown)'}")
         safe_print(f"{MAGIC_LINES[3]} Assembling {len(page_names)} pages…")

         # Build gz (or raw) bytes by concatenating page payloads
         assembled = bytearray()
+        per_page_sizes: List[Tuple[str,int]] = []

         for pn in page_names:
             meta = pages_by_name[pn]
             payload = meta.get("payload", [])
             page_bytes = payload_to_bytes(payload)
+            per_page_sizes.append((pn, len(page_bytes)))

             # Optional per-page sha
             page_sha = pick_hash(meta, ["sha", "sha256", "sha_gz", "sha_page"])
             if page_sha:
                 verify_optional(f"page {pn}", page_bytes, page_sha)

             assembled.extend(page_bytes)

         blob = bytes(assembled)
+        if args.debug:
+            safe_print("\nPer-page byte sizes:")
+            for pn, sz in per_page_sizes:
+                safe_print(f"  {pn}: {sz} bytes")
+            safe_print(f"\nTOTAL assembled bytes: {len(blob)}")
+            safe_print(f"[debug] first 8 bytes: {blob[:8].hex() if blob else '(empty)'}")

@@
         looks_gzip = len(blob) >= 2 and blob[0] == 0x1F and blob[1] == 0x8B
         if looks_gzip and not args.no_gunzip:
-            safe_print(MAGIC_LINES[5])
+            if args.debug:
+                safe_print("GZIP detected — decompressing…")
+            else:
+                safe_print(MAGIC_LINES[5])
             out_bytes = gzip.decompress(blob)
         else:
             out_bytes = blob
