#!/usr/bin/env python3
"""Seals, anchors, comments and verification."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import actors
import assertions
import fixtures
import preflight

ALICE = "pa"
BOB = "deployer"


def main() -> int:
    if not preflight.require_devnet("unit_provenance"):
        return 2
    for name in (ALICE, BOB):
        actors.ensure_vault(name)
    assertions.expect_ok("alice identity", fixtures.ensure_identity(ALICE, "alice-prov", "Alice"))

    reply = assertions.call(fixtures.comp("component:provenance-book"), "seal",
                            [__import__("terms").Raw("*dId"),
                             {"titleHash": "design-title", "docHash": "deadbeef",
                              "kind": "design"}], key=ALICE)
    assertions.expect_ok("seal", reply)
    seal_id = reply[1]

    reply = assertions.call(fixtures.comp("component:provenance-book"), "anchor",
                            [__import__("terms").Raw("*dId"), "ka:test",
                             {"kind": "inspection", "hash": "cafebabe"}], key=ALICE)
    assertions.expect_ok("anchor", reply)

    reply = assertions.call(fixtures.comp("component:provenance-book"), "verify",
                            ["ka:test", "cafebabe"], deployer=False)
    assertions.expect("verify anchor", reply, (True, True))
    reply = assertions.call(fixtures.comp("component:provenance-book"), "verify",
                            ["ka:test", "wrong"], deployer=False)
    assertions.expect("verify wrong", reply, (True, False))
    reply = assertions.call(fixtures.comp("component:provenance-book"), "verify",
                            [seal_id, "deadbeef"], deployer=False)
    assertions.expect("verify seal", reply, (True, True))

    reply = assertions.call(fixtures.comp("component:provenance-book"), "comment",
                            [__import__("terms").Raw("*dId"), "ka:test",
                             {"hash": "comment-hash"}], key=ALICE)
    assertions.expect_ok("comment", reply)

    reply = assertions.call(fixtures.comp("component:provenance-book"), "comment",
                            [__import__("terms").Raw("*dId"), "ka:test",
                             {"hash": "comment-hash"}], key=BOB)
    assertions.expect_refusal("unregistered comment", reply, "not registered")

    print("unit_provenance: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
