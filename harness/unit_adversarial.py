#!/usr/bin/env python3
"""Refusals that must survive an adversarial caller."""

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
from terms import Raw

ALICE = "alice"
DAVE = "dave"
MALLORY = "mallory"


def main() -> int:
    if not preflight.require_devnet("unit_adversarial"):
        return 2
    for name in (ALICE, DAVE, MALLORY):
        actors.ensure_vault(name)
    suffix = uuid.uuid4().hex[:8]
    mallory_subject = f"subject-mallory-{suffix}"

    issued = fixtures.issue("deployer", mallory_subject, "Validator",
                            "structural", "US-TX", "validator", 2)
    assertions.expect_ok("mallory credential", issued)
    reply = assertions.call(fixtures.comp("component:credential-book"), "revoke",
                            [Raw("*dId"), issued[1], "adversarial"], key="deployer")
    assertions.expect_ok("revoke mallory", reply)
    reply = fixtures.valid(mallory_subject, "Validator", "structural", "US-TX",
                           "validator", 2)
    assertions.expect("revoked credential", reply, (True, False, "not qualified"))

    assertions.expect_ok("dave risk credential",
                         fixtures.issue("deployer", actors.address(DAVE),
                                        "RiskAssessor", "structural", "US-TX",
                                        "risk", 2))
    bad = fixtures.assess(DAVE, "ka:adv-bad", 5, 5, 4, consequence_ref="")
    assertions.expect_ok("uninsurable", bad)
    assertions.expect("not insurable", bad[2], False)
    reply = assertions.call(fixtures.comp("component:risk-book"), "link",
                            [Raw("*dId"), bad[1], "ka:adv-bad"], key=DAVE)
    assertions.expect_refusal("uninsurable link", reply, "uninsurable")

    reply = fixtures.mint("ka:does-not-exist")
    assertions.expect_refusal("mint unknown kasset", reply, "unknown kasset")

    reply = assertions.call(fixtures.comp("component:kasset-book"), "oracleApprove",
                            ["cs:fake", "ka:fake"], deployer=False)
    assertions.expect_refusal("fake oracle approval", reply, "not decided")

    reply = fixtures.transfer(ALICE, actors.address(MALLORY), 10**15)
    assertions.expect("insufficient transfer refused",
                      isinstance(reply, tuple) and reply[0] is False, True)

    print("unit_adversarial: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
