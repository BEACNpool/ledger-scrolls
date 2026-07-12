import contextlib
import io
import json
import unittest
from unittest.mock import patch

import cbor2

from lsview import cli


POLICY = "8d6d38b3967028a15fc0e401b53c73a75ac654affc3f817c750c8b80"


def hex_name(name: str) -> str:
    return name.encode("utf-8").hex()


def head_nft(name: str, version: str, entries):
    return {
        "asset_name": hex_name(name),
        "asset_name_ascii": name,
        "minting_tx_hash": "ab" * 32,
        "minting_tx_metadata": {
            "721": {POLICY: {name: {"Type": "Registry Head", "Version": version}}},
            "22027": {"format": "ledger-scrolls-registry-list", "version": 2, "entries": entries},
        },
    }


ENTRIES = [
    {"n": "the-spec", "k": "manifest-chain-v2", "t": "e4" * 32, "i": 0},
    {"n": "hosky-png", "k": "utxo-inline-datum-bytes-v1", "t": "72" * 32, "i": 0},
    {"n": "bible", "k": "cip25-pages-v1", "p": "2f" * 28, "a": "BIBLE_MANIFEST"},
]


class RegistryNftResolutionTests(unittest.TestCase):
    def test_picks_highest_version_registry_head(self):
        assets = [
            {"asset_name": hex_name("LS_REGISTRY_V5")},
            {"asset_name": hex_name("LS_REGISTRY_V6")},
            {"asset_name": hex_name("BEACN_SIGIL")},
        ]
        rows = [
            head_nft("LS_REGISTRY_V5", "5", [ENTRIES[0]]),
            head_nft("LS_REGISTRY_V6", "6", ENTRIES),
        ]
        with patch.object(cli, "policy_asset_list", return_value=assets), \
             patch.object(cli, "asset_info_batch", return_value=rows) as batch:
            head, lst = cli.resolve_registry_nft(POLICY)
        # only REGISTRY-named assets get an asset_info lookup
        self.assertEqual(batch.call_args[0][1], [hex_name("LS_REGISTRY_V5"), hex_name("LS_REGISTRY_V6")])
        self.assertEqual(head["asset"], "LS_REGISTRY_V6")
        self.assertEqual(head["version"], 6)
        self.assertEqual(len(lst["entries"]), 3)

    def test_expands_compact_entries_to_pointer_shape(self):
        lst = cli._expand_registry_nft_entries({"version": 2, "entries": ENTRIES})
        self.assertEqual(lst["format"], "ledger-scrolls-registry-list")
        by_name = {e["name"]: e["pointer"] for e in lst["entries"]}
        self.assertEqual(by_name["the-spec"], {"kind": "manifest-chain-v2", "txHash": "e4" * 32, "txIx": 0})
        self.assertEqual(by_name["hosky-png"]["kind"], "utxo-inline-datum-bytes-v1")
        self.assertEqual(by_name["bible"], {"kind": "cip25-pages-v1", "policyId": "2f" * 28, "manifestAsset": "BIBLE_MANIFEST"})

    def test_no_registry_head_is_an_error(self):
        assets = [{"asset_name": hex_name("BEACN_CARD")}]
        rows = [{"asset_name": hex_name("BEACN_CARD"), "asset_name_ascii": "BEACN_CARD", "minting_tx_metadata": {}}]
        with patch.object(cli, "policy_asset_list", return_value=assets), \
             patch.object(cli, "asset_info_batch", return_value=rows):
            with self.assertRaisesRegex(cli.RegistryError, "registry head"):
                cli.resolve_registry_nft(POLICY)


class LegacyHeadTests(unittest.TestCase):
    def test_spent_head_warns_on_stderr(self):
        head = {"format": "ledger-scrolls-registry-head", "version": 0}
        datum_hex = cbor2.dumps(json.dumps(head).encode("utf-8")).hex()
        row = {"is_spent": True, "inline_datum": {"bytes": datum_hex}}
        err = io.StringIO()
        with patch.object(cli, "utxo_info", return_value=row), contextlib.redirect_stderr(err):
            out = cli.read_registry_head("00" * 32 + "#0")
        self.assertEqual(out["format"], "ledger-scrolls-registry-head")
        self.assertIn("spent", err.getvalue())
        self.assertIn("superseded", err.getvalue())


class MergeRegistryListTests(unittest.TestCase):
    def lst(self, *names_pointers):
        return {
            "format": "ledger-scrolls-registry-list",
            "entries": [{"name": n, "pointer": p} for n, p in names_pointers],
        }

    def test_private_overrides_public_and_appends(self):
        base = self.lst(("a", {"kind": "url", "url": "a1"}), ("b", {"kind": "url", "url": "b1"}))
        extra = self.lst(("b", {"kind": "url", "url": "b2"}), ("c", {"kind": "url", "url": "c1"}))
        merged = cli._merge_registry_lists(base, extra, extra_label="private[0]")
        names = [e["name"] for e in merged["entries"]]
        self.assertEqual(names, ["a", "b", "c"])
        by_name = {e["name"]: e for e in merged["entries"]}
        self.assertEqual(by_name["b"]["pointer"]["url"], "b2")
        self.assertEqual(by_name["b"]["_source"], "private[0]")
        self.assertEqual(by_name["a"]["_source"], "base")

    def test_invalid_format_rejected(self):
        with self.assertRaises(cli.RegistryError):
            cli._merge_registry_lists({"format": "nope"}, self.lst(), extra_label="x")


if __name__ == "__main__":
    unittest.main()
