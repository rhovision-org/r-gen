#!/usr/bin/env python3
"""Oracle case, panel selection, votes, tally and idempotent execution."""

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
FRANK = "frank"
MALLORY = "mallory"


def main() -> int:
    if not preflight.require_devnet("unit_oracle"):
        return 2
    for name in (DAVE, ERIN, FRANK, MALLORY):
        actors.ensure_vault(name)
    for name in (DAVE, ERIN, FRANK):
        assertions.expect_ok(f"{name} oracle credential",
                             fixtures.issue("deployer", actors.address(name),
                                            "Oracle", "structural", "US-TX",
                                            "oracle", 2))

    opened = fixtures.open_case(MALLORY, "liability", "ka:oracle-test", 3, 6666)
    assertions.expect_ok("open case", opened)
    case_id = opened[1]

    reply = assertions.call(fixtures.comp("component:oracle"), "empanel", [case_id],
                            deployer=False)
    assertions.expect_ok("empanel", reply)
    chosen = reply[1]
    assertions.expect("panel non-empty", len(chosen) > 0, True)

    reply = assertions.call(fixtures.comp("component:oracle"), "vote",
                            [__import__("terms").Raw("*dId"), case_id,
                             {"decision": "approve", "rationaleHash": "x"}],
                            key=MALLORY)
    assertions.expect_refusal("non-panelist vote", reply, "not panelist")

    panel = assertions.call(fixtures.comp("component:oracle"), "panelOf", [case_id],
                            deployer=False)
    assertions.expect_ok("panelOf", panel)
    by_address = {actors.address(name): name for name in (DAVE, ERIN, FRANK)}
    voters = []
    for member in panel[1]:
        subject = member.get("subject")
        if subject in by_address:
            voters.append(by_address[subject])
    assertions.expect("at least two mapped voters", len(voters) >= 2, True)

    first = voters[0]
    second = voters[1]
    reply = assertions.call(fixtures.comp("component:oracle"), "vote",
                            [__import__("terms").Raw("*dId"), case_id,
                             {"decision": "approve", "rationaleHash": "a"}],
                            key=first)
    assertions.expect_ok("first vote", reply)
    reply = assertions.call(fixtures.comp("component:oracle"), "vote",
                            [__import__("terms").Raw("*dId"), case_id,
                             {"decision": "approve", "rationaleHash": "a"}],
                            key=first)
    assertions.expect_refusal("double vote", reply, "already voted")

    reply = assertions.call(fixtures.comp("component:oracle"), "vote",
                            [__import__("terms").Raw("*dId"), case_id,
                             {"decision": "approve", "rationaleHash": "b"}],
                            key=second)
    assertions.expect_ok("second vote", reply)

    reply = assertions.call(fixtures.comp("component:oracle"), "tally", [case_id],
                            deployer=False)
    assertions.expect("tally approve", reply, (True, "approve"))

    reply = assertions.call(fixtures.comp("component:oracle"), "execute", [case_id],
                            deployer=False)
    assertions.expect_ok("execute", reply)
    reply = assertions.call(fixtures.comp("component:oracle"), "execute", [case_id],
                            deployer=False)
    assertions.expect_ok("execute idempotent", reply)

    reply = assertions.call(fixtures.comp("component:oracle"), "close", [case_id],
                            deployer=False)
    assertions.expect_ok("close", reply)

    print("unit_oracle: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
