#!/usr/bin/env python3
"""Validation, approval, rejection and nesting."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import actors
import assertions
import fixtures
import preflight
from terms import Raw

ALICE = "ka"
BOB = "kb"
CAROL = "kc"


def main() -> int:
    if not preflight.require_devnet("unit_kasset"):
        return 2
    for name in (ALICE, BOB, CAROL):
        actors.ensure_vault(name)
    for name, handle in ((ALICE, "alice-kasset"), (BOB, "bob-kasset"), (CAROL, "carol-kasset")):
        assertions.expect_ok(f"{name} identity", fixtures.ensure_identity(name, handle))
    assertions.expect_ok("validator", fixtures.issue("deployer", actors.address(BOB),
                                                     "Validator", "structural", "US-TX",
                                                     "validator", 2))
    assertions.expect_ok("approver", fixtures.issue("deployer", actors.address(CAROL),
                                                    "Approver", "structural", "US-TX",
                                                    "approver", 3))

    work = fixtures.open_work(ALICE, "kasset-work", "structural")
    claim = fixtures.claim(ALICE, work[1], "statement", "definition")
    validation = fixtures.validate(BOB, claim[1])
    assertions.expect_ok("validate", validation)
    kasset_id = validation[2]

    approval = fixtures.approve(CAROL, kasset_id)
    assertions.expect_ok("approve", approval)
    reply = fixtures.approve(CAROL, kasset_id)
    assertions.expect_refusal("approve twice", reply, "not validated")

    claim2 = fixtures.claim(ALICE, work[1], "statement2", "definition2")
    validation2 = fixtures.validate(BOB, claim2[1])
    kasset2 = validation2[2]
    assertions.expect_ok("approve child", fixtures.approve(CAROL, kasset2))

    reply = assertions.call(fixtures.comp("component:kasset-book"), "nest",
                            [Raw("*dId"), kasset_id, [kasset2]], key=ALICE)
    assertions.expect_ok("nest", reply)
    reply = assertions.call(fixtures.comp("component:kasset-book"), "nest",
                            [Raw("*dId"), kasset_id, [kasset2]], key=ALICE)
    assertions.expect_refusal("duplicate child", reply, "duplicate child")

    claim3 = fixtures.claim(ALICE, work[1], "statement3", "definition3")
    validation3 = fixtures.validate(BOB, claim3[1], verdict="invalid")
    kasset3 = validation3[2]
    reply = fixtures.approve(CAROL, kasset3)
    assertions.expect_refusal("approve rejected", reply, "not validated")

    print("unit_kasset: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
