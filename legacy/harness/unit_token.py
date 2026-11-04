#!/usr/bin/env python3
"""KAT mint, balances, reputation, transfer and insufficient balance."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import actors
import assertions
import fixtures
import preflight

ALICE = "ta"
BOB = "tb"
CAROL = "tc"


def main() -> int:
    if not preflight.require_devnet("unit_token"):
        return 2
    for name in (ALICE, BOB, CAROL):
        actors.ensure_vault(name)
        assertions.expect_ok(f"{name} identity",
                             fixtures.ensure_identity(name, f"{name}-token"))
    assertions.expect_ok("validator", fixtures.issue("deployer", actors.address(BOB),
                                                     "Validator", "structural", "US-TX",
                                                     "validator", 2))
    assertions.expect_ok("approver", fixtures.issue("deployer", actors.address(CAROL),
                                                    "Approver", "structural", "US-TX",
                                                    "approver", 2))

    work = fixtures.open_work(ALICE, "token-work", "structural")
    claim = fixtures.claim(ALICE, work[1], "s", "d")
    validation = fixtures.validate(BOB, claim[1])
    kasset = validation[2]
    assertions.expect_ok("approve", fixtures.approve(CAROL, kasset))

    alice = actors.address(ALICE)
    bob = actors.address(BOB)
    base_alice = fixtures.balance(alice)[1]
    base_bob = fixtures.balance(bob)[1]
    base_earned = fixtures.reputation(bob)[1].get("earned")

    minted = fixtures.mint(kasset)
    assertions.expect_ok("mint", minted)
    alice_amount = minted[1].get("claimantAmount")
    bob_amount = minted[1].get("validatorAmount")

    reply = fixtures.reputation(bob)
    assertions.expect("bob earned", reply[1].get("earned"), base_earned + bob_amount)
    assertions.expect("bob weight", reply[1].get("weightBps"), 10000)

    earned_alice = fixtures.reputation(alice)[1].get("earned")

    reply = fixtures.transfer(ALICE, bob, 1_000_000)
    assertions.expect_ok("transfer", reply)
    reply = fixtures.balance(alice)
    assertions.expect("alice balance", reply,
                      (True, base_alice + alice_amount - 1_000_000))
    reply = fixtures.balance(bob)
    assertions.expect("bob balance", reply,
                      (True, base_bob + bob_amount + 1_000_000))
    reply = fixtures.reputation(alice)
    assertions.expect("earned unchanged", reply[1].get("earned"), earned_alice)

    reply = fixtures.transfer(ALICE, actors.address(BOB), alice_amount * 2)
    assertions.expect("insufficient transfer refused",
                      isinstance(reply, tuple) and reply[0] is False, True)

    reply = fixtures.transfer(ALICE, actors.address(ALICE), 1)
    assertions.expect_refusal("self transfer", reply, "self")

    reply = fixtures.mint("ka:missing")
    assertions.expect_refusal("unknown kasset mint", reply, "unknown kasset")

    print("unit_token: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
