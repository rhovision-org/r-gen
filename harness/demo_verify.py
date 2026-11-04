#!/usr/bin/env python3
"""Verify every catalogue entry against the chain it names.

The catalogue is not trusted: each URI is read through the corresponding contract, and
the K-Asset/claim/case/provenance relationships are checked in both directions.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "tools"))

from terms import enc  # noqa: E402

DEVNET = json.loads((ROOT / "configs" / "devnet.json").read_text())
TESTNET = json.loads((ROOT / "configs" / "testnet.json").read_text())


def explore(node: str, uri: str, arm: str, args=()):
    call = ", ".join([json.dumps(arm), *(enc(arg) for arg in args), "*ret"])
    term = (
        "new reply, rl(`rho:registry:lookup`), ch, ret in { "
        f"rl!(`{uri}`, *ch) | "
        "for (C <- ch) { "
        f"C!({call}) | for (@r <- ret) {{ reply!(r) }} }} }}"
    )
    request = urllib.request.Request(
        f"{node.rstrip('/')}/api/v1/explore-deploy",
        data=json.dumps(term).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        expr = json.loads(response.read()).get("expr", [])
    return decode(expr[0]) if expr else None


def decode(value):
    if isinstance(value, dict):
        if "ExprBool" in value:
            return bool(value["ExprBool"]["data"])
        if "ExprInt" in value:
            return int(value["ExprInt"]["data"])
        if "ExprString" in value or "ExprUri" in value:
            return (value.get("ExprString") or value.get("ExprUri"))["data"]
        if "ExprTuple" in value:
            return tuple(decode(item) for item in value["ExprTuple"]["data"])
        if "ExprList" in value:
            return [decode(item) for item in value["ExprList"]["data"]]
        if "ExprMap" in value:
            data = value["ExprMap"]["data"]
            if isinstance(data, dict):
                return {key: decode(item) for key, item in data.items()}
            return {decode(entry["key"]): decode(entry["value"]) for entry in data}
        if "ExprPar" in value:
            return [decode(item) for item in value["ExprPar"]["data"]]
        return {key: decode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [decode(item) for item in value]
    return value


def ok(reply) -> bool:
    return isinstance(reply, tuple) and bool(reply) and reply[0] is True


def get(uri: str) -> dict:
    reply = explore(NODE, uri, "get")
    if not ok(reply) or not isinstance(reply[1], dict):
        raise AssertionError(f"get {uri}: {reply!r}")
    return reply[1]


def main() -> int:
    global NODE
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalogue", type=Path, default=ROOT / "deployments" / "catalogue.json")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--node", default=None)
    args = parser.parse_args()

    catalogue = json.loads(args.catalogue.read_text())
    manifest_path = args.manifest
    if manifest_path is None:
        manifest_path = (
            ROOT / "deployments" / "testnet.json"
            if catalogue.get("networkId") == TESTNET["networkId"]
            else ROOT / "deployments" / "devnet.json"
        )
    manifest = json.loads(manifest_path.read_text())
    components = manifest["components"]
    NODE = args.node or (
        TESTNET["node"] if catalogue.get("networkId") == TESTNET["networkId"] else DEVNET["node"]
    )
    if args.node is None and catalogue.get("networkId") not in (
        None,
        TESTNET["networkId"],
        "testnet",
    ):
        # The local node reports a small devnet network id; the catalogue records it.
        NODE = DEVNET["node"]

    entries = catalogue.get("entries", [])
    failures = 0
    for entry in entries:
        kind = entry.get("kind")
        uri = entry.get("uri")
        try:
            if kind == "identity":
                address = entry.get("detail")
                reply = explore(NODE, components["identity-directory"], "lookup", [address])
                if not ok(reply) or reply[1] != uri:
                    raise AssertionError(f"directory lookup {address}: {reply!r}")
            elif kind in ("credential", "claim", "value"):
                factory = {
                    "credential": components["credential-factory"],
                    "claim": components["claim-factory"],
                    "value": components["value-proposition-factory"],
                }[kind]
                reply = explore(NODE, factory, "verify", [uri])
                if not ok(reply):
                    raise AssertionError(f"factory verify: {reply!r}")
                get(uri)
            elif kind == "kasset":
                state = get(uri)
                claim_uri = (state.get("claimRef") or {}).get("uri")
                if claim_uri:
                    claim = get(claim_uri)
                    if (claim.get("kassetRef") or {}).get("uri") != uri:
                        raise AssertionError("claim does not point back to the K-Asset")
            elif kind == "case":
                state = get(uri)
                subject = (state.get("subjectRef") or {}).get("uri")
                if subject and subject.startswith("rho:id:"):
                    claim = get(subject)
                    kasset_uri = (claim.get("kassetRef") or {}).get("uri")
                    if kasset_uri:
                        kasset = get(kasset_uri)
                        if (kasset.get("dispute") or {}).get("id") != uri:
                            raise AssertionError("K-Asset does not point back to the case")
            elif kind == "provenance":
                state = get(uri)
                asset = (state.get("assetRef") or {}).get("uri")
                if not asset:
                    raise AssertionError("provenance has no assetRef")
                get(asset)
                if not state.get("anchors"):
                    raise AssertionError("provenance has no anchors")
            else:
                raise AssertionError(f"unknown kind {kind}")
            print(f"ok   {kind:12s} {entry.get('label', '')}")
        except (AssertionError, OSError, ValueError) as error:
            failures += 1
            print(f"FAIL {kind:12s} {entry.get('label', '')}: {error}")

    if failures:
        print(f"demo-verify: {failures} failure(s)", file=sys.stderr)
        return 4
    print(f"demo-verify: {len(entries)} entries verified on {NODE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
