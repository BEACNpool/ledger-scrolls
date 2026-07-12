import unittest
import urllib.error
from unittest.mock import patch

from lsview import koios


class WithRetriesTests(unittest.TestCase):
    def test_deterministic_koios_error_is_not_retried(self):
        calls = []

        def fn():
            calls.append(1)
            raise koios.KoiosError("UTxO not found: deadbeef#0")

        with self.assertRaisesRegex(koios.KoiosError, "not found"):
            koios.with_retries(fn)
        self.assertEqual(len(calls), 1)

    def test_http_4xx_is_not_retried(self):
        calls = []

        def fn():
            calls.append(1)
            raise urllib.error.HTTPError("http://x", 404, "not found", {}, None)

        with self.assertRaises(urllib.error.HTTPError):
            koios.with_retries(fn)
        self.assertEqual(len(calls), 1)

    def test_transient_urlerror_is_retried_then_succeeds(self):
        attempts = []

        def fn():
            attempts.append(1)
            if len(attempts) < 3:
                raise urllib.error.URLError("connection reset")
            return "ok"

        with patch.object(koios.time, "sleep") as sleep:
            self.assertEqual(koios.with_retries(fn, retries=5), "ok")
        self.assertEqual(len(attempts), 3)
        self.assertEqual(sleep.call_count, 2)

    def test_http_503_is_retried(self):
        attempts = []

        def fn():
            attempts.append(1)
            if len(attempts) < 2:
                raise urllib.error.HTTPError("http://x", 503, "unavailable", {}, None)
            return "ok"

        with patch.object(koios.time, "sleep"):
            self.assertEqual(koios.with_retries(fn), "ok")
        self.assertEqual(len(attempts), 2)

    def test_exhausted_retries_chain_the_original_exception(self):
        cause = urllib.error.URLError("network down")

        def fn():
            raise cause

        with patch.object(koios.time, "sleep"):
            with self.assertRaises(koios.KoiosError) as ctx:
                koios.with_retries(fn, retries=3)
        self.assertIs(ctx.exception.__cause__, cause)
        self.assertIn("3 attempts", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
