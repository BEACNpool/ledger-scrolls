#!/usr/bin/env python3
"""Validate registry documents against registry/schemas (requires jsonschema).

Covers the published on-chain mirrors, the conformance registry fixtures, and
the pointer fixtures, so the schema contract can never silently drift from
the live registry again. Offline: all $refs resolve from the local store.

Usage:
    python3 conformance/check_schemas.py
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SCHEMAS = REPO / "registry" / "schemas"

warnings.filterwarnings("ignore", category=DeprecationWarning)

FAILURES: list[str] = []
PASSES = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASSES
    if ok:
        PASSES += 1
        print(f"  PASS  {label}")
    else:
        FAILURES.append(label)
        print(f"  FAIL  {label}  {detail}")


def load(path: Path):
    return json.loads(path.read_text())


schemas = {p.name: load(p) for p in sorted(SCHEMAS.glob("*.schema.json"))}
store = {s["$id"]: s for s in schemas.values()}


def validator(schema_name: str) -> jsonschema.Draft202012Validator:
    schema = schemas[schema_name]
    resolver = jsonschema.RefResolver(base_uri=schema["$id"], referrer=schema, store=store)
    return jsonschema.Draft202012Validator(schema, resolver=resolver)


def validate(label: str, schema_name: str, doc, expect_valid: bool = True) -> None:
    errors = list(validator(schema_name).iter_errors(doc))
    if expect_valid:
        check(label, not errors, f"{len(errors)} error(s); first: {errors[0].message}" if errors else "")
    else:
        check(label, bool(errors), "validated but must not")


def main() -> int:
    print("== published on-chain mirrors ==")
    validate("registry/published/registry-list.json", "registry-list.schema.json",
             load(REPO / "registry" / "published" / "registry-list.json"))
    validate("registry/published/registry-head.json", "registry-head.schema.json",
             load(REPO / "registry" / "published" / "registry-head.json"))

    print("== conformance registry fixtures ==")
    validate("fixtures/registry/list.json", "registry-list.schema.json",
             load(ROOT / "fixtures" / "registry" / "list.json"))
    validate("fixtures/registry/head.json", "registry-head.schema.json",
             load(ROOT / "fixtures" / "registry" / "head.json"))

    print("== pointer fixtures ==")
    for f in sorted((ROOT / "fixtures" / "pointers" / "valid").glob("*.json")):
        validate(f"valid pointer validates: {f.name}", "pointer.schema.json", load(f))
    for f in sorted((ROOT / "fixtures" / "pointers" / "invalid").glob("*.json")):
        validate(f"invalid pointer fails: {f.name}", "pointer.schema.json", load(f),
                 expect_valid=False)

    print()
    print(f"{PASSES} passed, {len(FAILURES)} failed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
