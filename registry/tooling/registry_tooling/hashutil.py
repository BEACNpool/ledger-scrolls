import argparse
import hashlib
import json
from typing import Any


def canonical_json_bytes(obj: Any) -> bytes:
    """Deterministic JSON serialization.

    v0 rule: stable key ordering + no insignificant whitespace.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description="Compute canonical JSON SHA-256")
    ap.add_argument("path", help="Path to JSON file")
    args = ap.parse_args()

    with open(args.path, "rb") as f:
        raw = f.read()
    obj = json.loads(raw.decode("utf-8"))

    canon = canonical_json_bytes(obj)
    print(sha256_hex(canon))


if __name__ == "__main__":
    main()
