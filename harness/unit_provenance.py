#!/usr/bin/env python3
"""Provenance primitive: writer-only append-only anchors and comments."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import assertions
import corpus
import fixtures
import suite_base
from terms import Raw


def main() -> int:
    if not suite_base.require("unit_provenance"):
        return 2
    addrs = suite_base.setup(("alice", "bob"))

    created = fixtures.provenance_create(
        {"type": "kasset", "id": "asset-1", "uri": "rho:id:asset-1"},
        [addrs["alice"]])
    assertions.expect_ok("create provenance", created)
    prov_uri = created[1]["uri"]

    reply = fixtures.provenance_anchor(
        prov_uri, "alice", {"kind": "inspection", "hash": "aa", "parentHash": ""})
    assertions.expect_ok("anchor", reply)
    reply = fixtures.provenance_anchor(
        prov_uri, "alice", {"kind": "inspection", "hash": "aa", "parentHash": ""})
    assertions.expect_refusal("duplicate anchor refused", reply, "duplicate")
    corpus.assert_row("P1-anchor-duplicate", reply)
    reply = fixtures.provenance_anchor(
        prov_uri, "alice", {"kind": "inspection", "hash": "", "parentHash": ""})
    assertions.expect_refusal("empty hash refused", reply, "hash")
    reply = fixtures.provenance_anchor(
        prov_uri, "bob", {"kind": "inspection", "hash": "bb", "parentHash": ""})
    assertions.expect_refusal("non-writer anchor refused", reply, "not writer")

    reply = fixtures.provenance_anchor(
        prov_uri, "alice", {"kind": "photo", "hash": "bb", "parentHash": "aa"})
    assertions.expect_ok("second anchor", reply)
    reply = fixtures.read(prov_uri, "anchors")
    assertions.expect("two anchors", len(reply[1]), 2)

    reply = fixtures.call_uri(prov_uri, "verify", ["aa"], deployer=False)
    assertions.expect("verify known hash", reply, (True, True))
    corpus.assert_row("PROV-verify", reply)
    reply = fixtures.call_uri(prov_uri, "verify", ["zz"], deployer=False)
    assertions.expect("verify unknown hash", reply, (True, False))

    reply = fixtures.call_uri(prov_uri, "comment", [Raw("*dId"), {"hash": "note"}],
                              key="alice")
    assertions.expect_ok("writer comment", reply)
    corpus.assert_row("PROV-comment-writer", reply)
    reply = fixtures.call_uri(prov_uri, "comment", [Raw("*dId"), {"hash": "note"}],
                              key="bob")
    assertions.expect_refusal("non-writer comment refused", reply, "not writer")

    print("unit_provenance: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
