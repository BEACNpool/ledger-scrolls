import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest

from registry_tooling.verify import normalize_pointer, verify_name


def write_registry(tmp: str, payload: bytes, sha256: str):
    with open(os.path.join(tmp, "payload.bin"), "wb") as f:
        f.write(payload)
    lst = {
        "format": "ledger-scrolls-registry-list",
        "version": 0,
        "entries": [{
            "name": "payload",
            "pointer": {"kind": "url", "url": "./payload.bin"},
            "contentType": "application/octet-stream",
            "sha256": sha256,
        }],
    }
    with open(os.path.join(tmp, "list.json"), "w") as f:
        json.dump(lst, f)
    head = {
        "format": "ledger-scrolls-registry-head",
        "version": 0,
        "registryList": {"kind": "url", "url": "./list.json"},
    }
    head_path = os.path.join(tmp, "head.json")
    with open(head_path, "w") as f:
        json.dump(head, f)
    return head_path


class VerifyNameOfflineTests(unittest.TestCase):
    def test_end_to_end_ok(self):
        payload = b"a library that cannot burn"
        with tempfile.TemporaryDirectory() as tmp:
            head_path = write_registry(tmp, payload, hashlib.sha256(payload).hexdigest())
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                verify_name(head_path, "payload")
            report = json.loads(out.getvalue())
        self.assertTrue(report["ok"])
        self.assertEqual(report["headSigner"], "unsigned-v0")

    def test_hash_mismatch_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            head_path = write_registry(tmp, b"tampered bytes", "ab" * 32)
            with contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    verify_name(head_path, "payload")
        self.assertEqual(ctx.exception.code, 2)


class NormalizePointerTests(unittest.TestCase):
    def test_legacy_utxo_locked_bytes(self):
        p = normalize_pointer({"kind": "utxo-locked-bytes", "txin": "ab" * 32 + "#3"})
        self.assertEqual(p, {"kind": "utxo-inline-datum-bytes-v1", "txHash": "ab" * 32, "txIx": 3})

    def test_legacy_asset_manifest(self):
        p = normalize_pointer({"kind": "asset-manifest", "policyId": "cd" * 28, "assetName": "X_MANIFEST"})
        self.assertEqual(p, {"kind": "cip25-pages-v1", "policyId": "cd" * 28, "manifestAsset": "X_MANIFEST"})

    def test_canonical_pointer_untouched(self):
        p = {"kind": "url", "url": "./x.bin"}
        self.assertEqual(normalize_pointer(p), p)


if __name__ == "__main__":
    unittest.main()
