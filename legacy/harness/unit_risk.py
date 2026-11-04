#!/usr/bin/env python3
"""SPE scores, classes, insurability and attestation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import actors
import assertions
import fixtures
import preflight

DAVE = "dave"
ERIN = "erin"


def main() -> int:
    if not preflight.require_devnet("unit_risk"):
        return 2
    for name in (DAVE, ERIN):
        actors.ensure_vault(name)
    assertions.expect_ok("dave risk credential",
                         fixtures.issue("deployer", actors.address(DAVE),
                                        "RiskAssessor", "structural", "US-TX",
                                        "risk", 2))
    assertions.expect_ok("erin risk credential",
                         fixtures.issue("deployer", actors.address(ERIN),
                                        "RiskAssessor", "structural", "US-TX",
                                        "risk", 2))

    ass = fixtures.assess(DAVE, "ka:risk-test", 4, 3, 3)
    assertions.expect_ok("assess", ass)
    risk_id = ass[1]
    assertions.expect("insurable", ass[2], True)

    reply = assertions.call(fixtures.comp("component:risk-book"), "gate", [risk_id],
                            deployer=False)
    assertions.expect_ok("gate", reply)
    assertions.expect("score", reply[1].get("score"), 36)
    assertions.expect("class", reply[1].get("class"), "medium")
    assertions.expect("approver level", reply[1].get("approverLevel"), 2)

    reply = assertions.call(fixtures.comp("component:risk-book"), "attest",
                            [__import__("terms").Raw("*dId"), risk_id, "attest-hash"],
                            key=DAVE)
    assertions.expect_refusal("self attest", reply, "self attest")

    reply = assertions.call(fixtures.comp("component:risk-book"), "attest",
                            [__import__("terms").Raw("*dId"), risk_id, "attest-hash"],
                            key=ERIN)
    assertions.expect_ok("attest", reply)

    bad = fixtures.assess(DAVE, "ka:risk-bad", 4, 3, 3, probability_basis="")
    assertions.expect_ok("uninsurable assess", bad)
    assertions.expect("not insurable", bad[2], False)
    reply = assertions.call(fixtures.comp("component:risk-book"), "link",
                            [__import__("terms").Raw("*dId"), bad[1], "ka:risk-bad"],
                            key=ERIN)
    assertions.expect_refusal("link uninsurable", reply, "uninsurable")
    reply = assertions.call(fixtures.comp("component:risk-book"), "attest",
                            [__import__("terms").Raw("*dId"), bad[1], "x"], key=ERIN)
    assertions.expect_refusal("attest uninsurable", reply, "uninsurable")

    reply = fixtures.assess(DAVE, "ka:zero", 0, 3, 3)
    assertions.expect_refusal("zero factor", reply, "factor range")

    reply = assertions.call(fixtures.comp("component:risk-book"), "assess",
                            [__import__("terms").Raw("*dId"),
                             {"subjectRef": {"type": "kasset", "id": "ka:mech"},
                              "severity": 3, "probability": 3, "exposure": 3,
                              "discipline": "mechanical", "jurisdiction": "US-TX",
                              "exposureRef": "x", "probabilityBasis": "y",
                              "consequenceBasis": "z", "consequenceRef": "w",
                              "method": "USCG-SPE", "evidenceHash": ""}],
                            key=DAVE)
    assertions.expect_refusal("wrong discipline", reply, "not qualified")

    print("unit_risk: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
