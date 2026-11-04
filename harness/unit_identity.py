#!/usr/bin/env python3
"""Identity primitive: first-writer-wins directory, owner-only update."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import actors
import assertions
import fixtures
import suite_base
from terms import Raw


def main() -> int:
    if not suite_base.require("unit_identity"):
        return 2
    addrs = suite_base.setup(("alice", "bob", "carol"))

    reply = fixtures.call_uri(fixtures.comp("identity-directory"), "lookup",
                              [addrs["alice"]], deployer=False)
    assertions.expect_ok("alice directory lookup", reply)
    alice_uri = reply[1]

    reply = fixtures.identity("alice", "alice-second")
    assertions.expect_refusal("duplicate identity refused", reply, "duplicate")

    reply = fixtures.call_uri(alice_uri, "get", [], deployer=False)
    assertions.expect_ok("identity get", reply)
    assertions.expect("identity subject", reply[1].get("subject"), actors.address("alice"))

    patch = {"displayNameHash": "display-2", "orgHash": "org-2", "contactHash": "contact-2"}
    reply = fixtures.call_uri(alice_uri, "update", [Raw("*dId"), patch], key="alice")
    assertions.expect_ok("owner update", reply)
    reply = fixtures.call_uri(alice_uri, "get", [], deployer=False)
    assertions.expect("owner update stored", reply[1].get("displayNameHash"), "display-2")

    reply = fixtures.call_uri(alice_uri, "update", [Raw("*dId"), patch], key="bob")
    assertions.expect_refusal("non-owner update refused", reply, "not owner")

    reply = fixtures.call_uri(fixtures.comp("identity-directory"), "count", [],
                              deployer=False)
    assertions.expect_ok("identity count", reply)
    assertions.expect("at least three identities", reply[1] >= 3, True)

    print("unit_identity: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
