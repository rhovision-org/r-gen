#!/usr/bin/env python3
"""Credential issuance, scope matching, expiry, revocation and pool selection."""

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

BOB = "bob"
CAROL = "carol"
DAVE = "dave"


def main() -> int:
    if not preflight.require_devnet("unit_credentials"):
        return 2
    actors.ensure_vault(BOB)

    suffix = uuid.uuid4().hex[:8]
    bob = f"subject-bob-{suffix}"
    carol = f"subject-carol-{suffix}"
    dave = f"subject-dave-{suffix}"

    reply = fixtures.issue("deployer", bob, "Validator", "structural", "US-TX",
                           "validator", 2)
    assertions.expect_ok("issue validator", reply)
    cred = reply[1]

    reply = fixtures.valid(bob, "Validator", "structural", "US-TX", "validator", 2)
    assertions.expect("validator valid", reply, (True, True, cred))

    reply = fixtures.valid(bob, "Validator", "mechanical", "US-TX", "validator", 2)
    assertions.expect("wrong discipline", reply, (True, False, "not qualified"))

    reply = fixtures.issue(BOB, bob, "Validator", "structural", "US-TX",
                           "validator", 2)
    assertions.expect_refusal("self issue by non-issuer", reply, "unknown issuer")

    reply = fixtures.issue("deployer", carol, "Approver", "structural", "US-TX",
                           "approver", 3)
    assertions.expect_ok("issue approver", reply)

    reply = fixtures.issue("deployer", dave, "Oracle", "structural", "US-TX",
                           "oracle", 1)
    assertions.expect_ok("issue oracle level 1", reply)

    reply = fixtures.issue("deployer", dave, "Oracle", "structural", "US-TX",
                           "oracle", 2)
    assertions.expect_ok("issue oracle", reply)

    reply = fixtures.issue("deployer", bob, "Validator", "structural", "US-TX",
                           "validator", 4)
    assertions.expect_refusal("level range", reply, "level")

    reply = fixtures.issue("deployer", bob, "Validator", "structural", "US-TX",
                           "validator", 1, expires_at=1)
    assertions.expect_ok("issue expired", reply)
    expired = reply[1]
    reply = fixtures.valid(bob, "Validator", "structural", "US-TX", "validator", 1)
    assertions.expect_ok("expired ignored", reply)
    assertions.expect("expired one is not qualified", reply[1], True)
    assertions.expect("expired still has the earlier live credential",
                      reply[2], cred)

    reply = assertions.call(fixtures.comp("component:credential-book"), "revoke",
                            [__import__("terms").Raw("*dId"), cred, "test"],
                            key="deployer")
    assertions.expect_ok("revoke", reply)
    reply = fixtures.valid(bob, "Validator", "structural", "US-TX", "validator", 2)
    assertions.expect("revoked is not qualified", reply, (True, False, "not qualified"))

    reply = assertions.call(fixtures.comp("component:credential-book"), "pool",
                            [{"ctype": "Oracle", "discipline": "structural",
                              "jurisdiction": "US-TX", "role": "oracle",
                              "minLevel": 2}], deployer=False)
    assertions.expect_ok("pool", reply)
    assertions.expect("dave in oracle pool", dave in reply[1], True)

    print("unit_credentials: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
