import unittest

from lsview.catalog import CatalogError, DEFAULT_CATALOG, load_catalog


class CatalogTests(unittest.TestCase):
    def test_default_catalog_exists_and_loads(self):
        self.assertTrue(DEFAULT_CATALOG.is_file(), f"missing shipped catalog: {DEFAULT_CATALOG}")
        catalog = load_catalog()
        self.assertGreaterEqual(len(catalog), 22)

    def test_default_catalog_covers_documented_ids(self):
        catalog = load_catalog()
        self.assertEqual(catalog["hosky-png"].data["type"], "utxo_datum_bytes_v1")
        self.assertTrue(catalog["hosky-png"].data["tx_hash"])
        self.assertEqual(catalog["constitution-e608"].data["type"], "cip25_pages_v1")
        self.assertTrue(catalog["constitution-e608"].data["policy_id"])
        self.assertEqual(catalog["the-spec"].data["type"], "manifest_chain_v2")

    def test_missing_catalog_is_a_clear_error(self):
        with self.assertRaisesRegex(CatalogError, "--catalog"):
            load_catalog("/nonexistent/scrolls.json")

    def test_invalid_json_is_a_clear_error(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".json") as f:
            f.write("{not json")
            f.flush()
            with self.assertRaisesRegex(CatalogError, "not valid JSON"):
                load_catalog(f.name)


if __name__ == "__main__":
    unittest.main()
