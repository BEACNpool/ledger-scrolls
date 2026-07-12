import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from lsview import cli


ROOT = Path(__file__).resolve().parents[2] / "conformance"


def row(datum_hex: str):
    return {"inline_datum": {"bytes": datum_hex.strip()}}


class StandardDatumConformanceTests(unittest.TestCase):
    """Pin the lsview standard-scroll decoder to the shared fixture corpus,
    including the plutus-constructor (tag 121) shape cardano-cli emits."""

    def test_all_conformance_datum_vectors(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        vectors = manifest["vectors"]["datums"]
        self.assertGreaterEqual(len(vectors), 3)
        for v in vectors:
            datum_hex = (ROOT / v["file"]).read_text().strip()
            with patch.object(cli, "utxo_info", return_value=row(datum_hex)):
                data, sha = cli.reconstruct_standard_from_txin("00" * 32 + "#0")
            self.assertEqual(sha, v["decodedSha256"], v["file"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), v["decodedSha256"], v["file"])

    def test_expected_sha_mismatch_raises(self):
        datum_hex = (ROOT / "fixtures/datums/standard-datum-001.hex").read_text().strip()
        with patch.object(cli, "utxo_info", return_value=row(datum_hex)):
            with self.assertRaises(cli.RegistryError):
                cli.reconstruct_standard_from_txin("00" * 32 + "#0", expected_sha256="ab" * 32)

    def test_lookalike_address_is_rejected(self):
        datum_hex = (ROOT / "fixtures/datums/standard-datum-001.hex").read_text().strip()
        bad = row(datum_hex)
        bad["address"] = "addr1qxlookalike"
        with patch.object(cli, "utxo_info", return_value=bad):
            with self.assertRaisesRegex(cli.RegistryError, "always-fail"):
                cli.reconstruct_standard_from_txin("00" * 32 + "#0")


if __name__ == "__main__":
    unittest.main()
