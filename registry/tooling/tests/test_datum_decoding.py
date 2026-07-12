import hashlib
import json
from pathlib import Path
import unittest

from registry_tooling.verify import _decode_cbor_bytestring


ROOT = Path(__file__).resolve().parents[3] / "conformance"


class StandardDatumConformanceTests(unittest.TestCase):
    """Pin _decode_cbor_bytestring to the shared fixture corpus, including
    the plutus-constructor (tag 121) shape cardano-cli emits."""

    def test_all_conformance_datum_vectors(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        vectors = manifest["vectors"]["datums"]
        self.assertGreaterEqual(len(vectors), 3)
        for v in vectors:
            raw = bytes.fromhex((ROOT / v["file"]).read_text().strip())
            decoded = _decode_cbor_bytestring(raw)
            self.assertEqual(hashlib.sha256(decoded).hexdigest(), v["decodedSha256"], v["file"])

    def test_non_bytestring_input_passes_through(self):
        self.assertEqual(_decode_cbor_bytestring(b""), b"")
        self.assertEqual(_decode_cbor_bytestring(b"\x01\x02"), b"\x01\x02")

    def test_truncated_constructor_passes_through(self):
        raw = bytes.fromhex((ROOT / "fixtures/datums/standard-datum-003-plutus-constructor.hex").read_text().strip())
        truncated = raw[:-1]
        self.assertEqual(_decode_cbor_bytestring(truncated), truncated)


if __name__ == "__main__":
    unittest.main()
