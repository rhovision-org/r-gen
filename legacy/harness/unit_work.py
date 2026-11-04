#!/usr/bin/env python3
"""Work elements and claims: ownership, amend, withdraw and quantity checks."""

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

ALICE = "wa"
BOB = "wb"


def main() -> int:
    if not preflight.require_devnet("unit_work"):
        return 2
    for name in (ALICE, BOB):
        actors.ensure_vault(name)
    assertions.expect_ok("alice identity", fixtures.ensure_identity(ALICE, "alice-work", "Alice"))

    work = fixtures.open_work(ALICE, "work-title", "structural")
    assertions.expect_ok("open work", work)
    work_id = work[1]

    claim = fixtures.claim(ALICE, work_id, "statement", "definition")
    assertions.expect_ok("claim", claim)
    claim_id = claim[1]

    reply = assertions.call(fixtures.comp("component:work-book"), "amend",
                            [Raw("*dId"), claim_id,
                             {"statementHash": "statement2", "definitionHash": "definition2",
                              "quantity": {"unit": "inspections", "value": 13},
                              "evidence": []}],
                            key=ALICE)
    assertions.expect_ok("amend", reply)

    assertions.expect_ok("bob identity", fixtures.ensure_identity(BOB, "bob-work", "Bob"))
    reply = assertions.call(fixtures.comp("component:work-book"), "amend",
                            [Raw("*dId"), claim_id,
                             {"statementHash": "x", "definitionHash": "y",
                              "quantity": {"unit": "u", "value": 1}, "evidence": []}],
                            key=BOB)
    assertions.expect_refusal("non-claimant amend", reply, "not claimant")

    reply = assertions.call(fixtures.comp("component:work-book"), "withdraw",
                            [Raw("*dId"), claim_id], key=BOB)
    assertions.expect_refusal("non-claimant withdraw", reply, "not claimant")

    reply = assertions.call(fixtures.comp("component:work-book"), "claim",
                            [Raw("*dId"), "wk:missing",
                             {"ctype": "x", "statementHash": "s", "definitionHash": "d",
                              "quantity": {"unit": "u", "value": 1}, "evidence": [],
                              "riskRef": None, "supersedes": None}],
                            key=ALICE)
    assertions.expect_refusal("unknown work", reply, "unknown work")

    reply = assertions.call(fixtures.comp("component:work-book"), "claim",
                            [Raw("*dId"), work_id,
                             {"ctype": "x", "statementHash": "s", "definitionHash": "d",
                              "quantity": {"unit": "u", "value": -1}, "evidence": [],
                              "riskRef": None, "supersedes": None}],
                            key=ALICE)
    assertions.expect_refusal("negative quantity", reply, "quantity")

    reply = assertions.call(fixtures.comp("component:work-book"), "withdraw",
                            [Raw("*dId"), claim_id], key=ALICE)
    assertions.expect_ok("withdraw", reply)

    print("unit_work: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
