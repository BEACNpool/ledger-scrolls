import gzip
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from lsview import cli


ROOT = Path(__file__).resolve().parents[2] / "conformance"


def koios_rows_from_fixture(meta: dict, policy_id: str):
    """Build policy_asset_list + asset_info_batch shapes from a 721 fixture."""
    policy_meta = meta["721"][policy_id]
    assets, rows = [], []
    for asset_ascii in policy_meta:
        name_hex = asset_ascii.encode("utf-8").hex()
        assets.append({"asset_name": name_hex})
        rows.append({
            "asset_name": name_hex,
            "asset_name_ascii": asset_ascii,
            "minting_tx_hash": "ab" * 32,
            "minting_tx_metadata": meta,
        })
    return assets, rows


class Cip25ConformanceTests(unittest.TestCase):
    """Pin the live CIP-25 reconstruction path to the shared fixture corpus."""

    def test_all_conformance_cip25_vectors(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        for v in manifest["vectors"]["cip25"]:
            meta = json.loads((ROOT / v["file"]).read_text())
            assets, rows = koios_rows_from_fixture(meta, v["policyId"])
            with patch.object(cli, "policy_asset_list", return_value=assets), \
                 patch.object(cli, "asset_info_batch", return_value=rows), \
                 patch.object(cli, "tx_metadata", return_value={}):
                data, sha = cli.reconstruct_legacy_cip25(v["policyId"])
            self.assertEqual(sha, v["reconstructedSha256"], v["file"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), v["reconstructedSha256"], v["file"])

    def test_gzip_bomb_is_capped(self):
        bomb = gzip.compress(b"\x00" * 4_000_000)
        with self.assertRaisesRegex(cli.RegistryError, "safe limit"):
            cli.gunzip_capped(bomb, hard_limit=1_000_000)

    def test_gunzip_capped_roundtrip(self):
        raw = b"ledger-scrolls" * 64
        self.assertEqual(cli.gunzip_capped(gzip.compress(raw)), raw)

    def test_malformed_segment_hex_is_a_registry_error(self):
        meta = json.loads((ROOT / "fixtures/cip25/vector-001-metadata.json").read_text())
        policy = next(iter(meta["721"]))
        meta["721"][policy]["VEC001_P0001"]["payload"][0] = "0xNOTHEX"
        assets, rows = koios_rows_from_fixture(meta, policy)
        with patch.object(cli, "policy_asset_list", return_value=assets), \
             patch.object(cli, "asset_info_batch", return_value=rows), \
             patch.object(cli, "tx_metadata", return_value={}):
            with self.assertRaisesRegex(cli.RegistryError, "Malformed hex"):
                cli.reconstruct_legacy_cip25(policy)


if __name__ == "__main__":
    unittest.main()
