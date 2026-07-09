import gzip
from pathlib import Path
import unittest
from unittest.mock import patch

import cbor2

from lsview import cli


FIXTURES = Path(__file__).resolve().parents[2] / "conformance" / "fixtures" / "chain"


def row(hex_text: str):
    return {"inline_datum": {"bytes": hex_text.strip()}}


class ChainSafetyTests(unittest.TestCase):
    def test_bounded_gzip_accepts_exact_declared_size(self):
        raw = b"ledger-scrolls" * 100
        self.assertEqual(cli.gunzip_bounded(gzip.compress(raw), len(raw)), raw)

    def test_bounded_gzip_rejects_false_small_size(self):
        raw = b"x" * 10000
        with self.assertRaises(cli.RegistryError):
            cli.gunzip_bounded(gzip.compress(raw), 100)

    def test_manifest_cycle_is_rejected(self):
        head = (FIXTURES / "vector-004-head.hex").read_text()
        with patch.object(cli, "utxo_info", return_value=row(head)):
            with self.assertRaisesRegex(cli.RegistryError, "cycle"):
                cli.reconstruct_chain_from_txin("00" * 32 + "#0")

    def test_continuation_field_drift_is_rejected(self):
        head = (FIXTURES / "vector-004-head.hex").read_text()
        tail_raw = bytes.fromhex((FIXTURES / "vector-004-tail.hex").read_text().strip())
        tail = cbor2.loads(tail_raw)
        fields = list(tail.value)
        fields[1] = b"application/x-wrong"
        bad_tail = cbor2.dumps(cbor2.CBORTag(tail.tag, fields)).hex()
        responses = [row(head), row(bad_tail)]
        with patch.object(cli, "utxo_info", side_effect=responses):
            with self.assertRaisesRegex(cli.RegistryError, "contentType mismatch"):
                cli.reconstruct_chain_from_txin("00" * 32 + "#0")


if __name__ == "__main__":
    unittest.main()

