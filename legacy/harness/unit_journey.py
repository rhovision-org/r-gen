#!/usr/bin/env python3
"""The vertical slice: credential -> work -> claim -> validate -> approve -> mint."""

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

ALICE = "alice"
BOB = "bob"
CAROL = "carol"


def main() -> int:
    if not preflight.require_devnet("unit_journey"):
        return 2
    for name in (ALICE, BOB, CAROL):
        actors.ensure_vault(name)

    alice = actors.address(ALICE)
    bob = actors.address(BOB)
    carol = actors.address(CAROL)
    suffix = uuid.uuid4().hex[:8]

    assertions.expect_ok("alice identity",
                         fixtures.ensure_identity(ALICE, f"alice-journey-{suffix}", "Alice"))
    assertions.expect_ok("bob identity",
                         fixtures.ensure_identity(BOB, f"bob-journey-{suffix}", "Bob"))
    assertions.expect_ok("carol identity",
                         fixtures.ensure_identity(CAROL, f"carol-journey-{suffix}", "Carol"))

    assertions.expect_ok("validator credential",
                         fixtures.issue("deployer", bob, "Validator", "structural",
                                        "US-TX", "validator", 2))
    assertions.expect_ok("approver credential",
                         fixtures.issue("deployer", carol, "Approver", "structural",
                                        "US-TX", "approver", 3))

    work = fixtures.open_work(ALICE, "bridge-deck-inspection", "structural")
    assertions.expect_ok("open work", work)
    work_id = work[1]

    claim = fixtures.claim(ALICE, work_id, "deck inspected", "12 inspections at hold point")
    assertions.expect_ok("claim", claim)
    claim_id = claim[1]

    validation = fixtures.validate(BOB, claim_id)
    assertions.expect_ok("validate", validation)
    validation_id, kasset_id = validation[1], validation[2]

    approval = fixtures.approve(CAROL, kasset_id)
    assertions.expect_ok("approve", approval)
    approval_id = approval[1]
    print(f"  ids: claim={claim_id} validation={validation_id} "
          f"kasset={kasset_id} approval={approval_id}")

    base_alice = fixtures.balance(alice)[1]
    base_bob = fixtures.balance(bob)[1]
    base_earned = fixtures.reputation(bob)[1].get("earned")
    supply = assertions.call(fixtures.comp("component:token"), "supply", [],
                             deployer=False)
    base_supply = supply[1]

    minted = fixtures.mint(kasset_id)
    assertions.expect_ok("mint", minted)
    claimant_amount = minted[1].get("claimantAmount")
    validator_amount = minted[1].get("validatorAmount")
    assertions.expect("claimant amount positive", claimant_amount > 0, True)
    assertions.expect("validator amount positive", validator_amount > 0, True)

    reply = fixtures.balance(alice)
    assertions.expect("alice KAT balance", reply, (True, base_alice + claimant_amount))
    reply = fixtures.balance(bob)
    assertions.expect("bob KAT balance", reply, (True, base_bob + validator_amount))

    reply = fixtures.reputation(bob)
    assertions.expect_ok("bob reputation", reply)
    assertions.expect("bob earned", reply[1].get("earned"),
                      base_earned + validator_amount)

    supply = assertions.call(fixtures.comp("component:token"), "supply", [],
                             deployer=False)
    assertions.expect_ok("supply", supply)
    supply_before = base_supply + claimant_amount + validator_amount
    assertions.expect("supply after mint", supply[1], supply_before)

    transfer = fixtures.transfer(ALICE, bob, 1_000_000, "receipt transfer")
    assertions.expect_ok("transfer", transfer)

    reply = fixtures.balance(alice)
    assertions.expect("alice after transfer", reply,
                      (True, base_alice + claimant_amount - 1_000_000))
    reply = fixtures.balance(bob)
    assertions.expect("bob after transfer", reply,
                      (True, base_bob + validator_amount + 1_000_000))
    reply = fixtures.reputation(bob)
    assertions.expect("transfer does not change earned", reply[1].get("earned"),
                      base_earned + validator_amount)
    supply = assertions.call(fixtures.comp("component:token"), "supply", [],
                             deployer=False)
    assertions.expect("supply conserved", supply[1], supply_before)

    reply = fixtures.mint(kasset_id)
    assertions.expect_refusal("double mint", reply, "already minted")

    claim2 = fixtures.claim(ALICE, work_id, "second element", "handrail")
    assertions.expect_ok("second claim", claim2)
    assertions.expect_ok("validate second claim", fixtures.validate(BOB, claim2[1]))
    reply = fixtures.validate(BOB, claim2[1])
    assertions.expect_refusal("second validation", reply, "not open")

    # A qualified validator may not validate their own claim.
    assertions.expect_ok("alice validator credential",
                         fixtures.issue("deployer", alice, "Validator", "structural",
                                        "US-TX", "validator", 1))
    work2 = fixtures.open_work(ALICE, "self-work", "structural")
    claim3 = fixtures.claim(ALICE, work2[1], "self claim", "self definition")
    reply = fixtures.validate(ALICE, claim3[1])
    assertions.expect_refusal("self validation", reply, "self validation")

    # An approver is not a validator.
    work3 = fixtures.open_work(ALICE, "third-work", "structural")
    claim4 = fixtures.claim(ALICE, work3[1], "third claim", "third definition")
    reply = fixtures.validate(CAROL, claim4[1])
    assertions.expect_refusal("unqualified validator", reply, "not qualified")

    print("unit_journey: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
