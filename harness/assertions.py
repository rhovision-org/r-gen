#!/usr/bin/env python3
"""Assertion and manifest helpers shared by the behavioural suites."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import deploy as node  # noqa: E402
import terms  # noqa: E402

MANIFEST = ROOT / "deployments" / "devnet.json"


def decode(value):
    if isinstance(value, list):
        return [decode(item) for item in value]
    if isinstance(value, dict):
        if "ExprString" in value:
            return value["ExprString"]["data"]
        if "ExprUri" in value:
            return value["ExprUri"]["data"]
        if "ExprInt" in value:
            return int(value["ExprInt"]["data"])
        if "ExprBool" in value:
            return bool(value["ExprBool"]["data"])
        if "ExprTuple" in value:
            return tuple(decode(item) for item in value["ExprTuple"]["data"])
        if "ExprList" in value:
            return [decode(item) for item in value["ExprList"]["data"]]
        if "ExprSet" in value:
            return [decode(item) for item in value["ExprSet"]["data"]]
        if "ExprMap" in value:
            data = value["ExprMap"]["data"]
            if isinstance(data, dict):
                return {key: decode(item) for key, item in data.items()}
            return {decode(entry["key"]): decode(entry["value"]) for entry in data}
        if "ExprByteArray" in value:
            return bytes.fromhex(value["ExprByteArray"]["data"])
        if "ExprBytes" in value:
            return bytes.fromhex(value["ExprBytes"]["data"])
        return {key: decode(item) for key, item in value.items()}
    return value


def manifest() -> dict:
    if not MANIFEST.is_file():
        raise SystemExit(f"missing {MANIFEST}; run `make install`")
    return json.loads(MANIFEST.read_text())


def root_uri() -> str:
    return manifest()["root_uri"]


def find_uri(value) -> str | None:
    if isinstance(value, str):
        return value if value.startswith("rho:id:") else None
    if isinstance(value, (list, tuple)):
        for item in value:
            found = find_uri(item)
            if found:
                return found
    if isinstance(value, dict):
        for item in value.values():
            found = find_uri(item)
            if found:
                return found
    return None


def component_uri(file_name: str) -> str:
    entry = manifest().get("components", {}).get(file_name)
    uri = find_uri(entry)
    if not uri:
        raise SystemExit(f"no URI for {file_name} in the install manifest")
    return uri


def secret(name: str = "deployer") -> str:
    return node.secret_for(name)


def one(term: str, key: str = "deployer", phlo_limit: int = 8_000_000):
    deploy_id, result = node.deploy_and_wait(term, secret(key), phlo_limit=phlo_limit)
    decoded = decode(result)
    if isinstance(decoded, list) and len(decoded) == 1:
        return decoded[0]
    return decoded


def call(uri: str, arm: str, args=(), key: str = "deployer",
         deployer: bool = True, phlo_limit: int = 8_000_000):
    if deployer:
        term = terms.call_term(uri, arm, args)
    else:
        term = terms.call_no_deployer(uri, arm, args)
    return one(term, key=key, phlo_limit=phlo_limit)


def resolve(component: str, key: str = "deployer"):
    from actors import resolve as actor_resolve
    return actor_resolve(component, key=key)


def expect(label: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
    print(f"  ok {label}")


def expect_refusal(label: str, actual, reason: str) -> None:
    if not (isinstance(actual, tuple) and len(actual) >= 2
            and actual[0] is False and actual[1] == reason):
        raise AssertionError(f"{label}: expected (false, {reason!r}), got {actual!r}")
    print(f"  ok {label}")


def expect_ok(label: str, actual) -> None:
    if not (isinstance(actual, tuple) and len(actual) >= 1 and actual[0] is True):
        raise AssertionError(f"{label}: expected (true, ...), got {actual!r}")
    print(f"  ok {label}")
