#!/usr/bin/env python3
"""Identity registration, handles, updates and count."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import actors
import assertions
import fixtures
import preflight

ALICE = "ida"
BOB = "idb"


def main() -> int:
    if not preflight.require_devnet("unit_identity"):
        return 2
    for name in (ALICE, BOB):
        actors.ensure_vault(name)

    alice = actors.address(ALICE)
    bob = actors.address(BOB)

    assertions.expect_ok("alice identity",
                         fixtures.ensure_identity(ALICE, "alice-identity", "Alice"))
    reply = assertions.call(fixtures.comp("component:identity"), "profile", [alice],
                            deployer=False)
    assertions.expect_ok("profile", reply)
    handle = reply[1].get("handle")

    reply = fixtures.identity(ALICE, handle, "Alice")
    assertions.expect_refusal("duplicate identity", reply, "duplicate")

    # idb is fresh for this suite; it may not take ida's handle.
    reply = fixtures.identity(BOB, handle, "Bob")
    assertions.expect_refusal("handle taken", reply, "handle taken")

    reply = assertions.call(fixtures.comp("component:identity"), "byHandle",
                            [handle], deployer=False)
    assertions.expect("byHandle", reply, (True, alice))

    reply = assertions.call(fixtures.comp("component:identity"), "byHandle",
                            ["nobody"], deployer=False)
    assertions.expect_refusal("unknown handle", reply, "unknown handle")

    reply = assertions.call(fixtures.comp("component:identity"), "update",
                            [__import__("terms").Raw("*dId"),
                             {"displayName": "Alice Updated", "orgHash": "org",
                              "contactHash": "contact"}],
                            key=ALICE)
    assertions.expect_ok("update", reply)

    assertions.expect_ok("bob identity",
                         fixtures.ensure_identity(BOB, f"bob-{uuid.uuid4().hex[:8]}", "Bob"))

    reply = assertions.call(fixtures.comp("component:identity"), "count", [],
                            deployer=False)
    assertions.expect_ok("count", reply)
    assertions.expect("count at least two", reply[1] >= 2, True)

    print("unit_identity: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
