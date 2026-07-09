import copy
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from registry_tooling.hashutil import canonical_json_bytes
from registry_tooling.verify import RegistryError, rotation_allows, verify_head_signature


class SignedHeadTests(unittest.TestCase):
    def signed(self, key, next_keys=None):
        pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        head = {"format":"ledger-scrolls-registry-head","version":1,
                "registryList":{"kind":"url","url":"./list.json"},
                "signer":{"keyId":pub,"nextKeys":next_keys or []}}
        head["signature"] = key.sign(canonical_json_bytes(head)).hex()
        return head

    def test_valid_and_pinned_signature(self):
        key=Ed25519PrivateKey.generate(); head=self.signed(key)
        self.assertEqual(verify_head_signature(head, head["signer"]["keyId"]), head["signer"]["keyId"])

    def test_tamper_and_wrong_pin_fail(self):
        key=Ed25519PrivateKey.generate(); head=self.signed(key)
        bad=copy.deepcopy(head); bad["version"]=2
        with self.assertRaises(RegistryError): verify_head_signature(bad)
        with self.assertRaises(RegistryError): verify_head_signature(head, "00"*32)

    def test_rotation(self):
        old=Ed25519PrivateKey.generate(); new=Ed25519PrivateKey.generate()
        new_pub=new.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        self.assertTrue(rotation_allows(self.signed(old,[new_pub]),self.signed(new)))


if __name__ == "__main__": unittest.main()
