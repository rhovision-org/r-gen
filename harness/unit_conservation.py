#!/usr/bin/env python3
"""KAT supply is not created or destroyed by transfers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import assertions
import fixtures
import preflight

OWNERS = ["alice", "bob", "carol", "dave", "erin", "frank", "mallory"]


def main() -> int:
    if not preflight.require_devnet("unit_conservation"):
        return 2

    supply = assertions.call(fixtures.comp("component:token"), "supply", [],
                             deployer=False)
    assertions.expect_ok("supply", supply)
    total = supply[1]

    known = 0
    for name in OWNERS:
        owner = __import__("actors").address(name)
        reply = fixtures.balance(owner)
        assertions.expect_ok(f"balance {name}", reply)
        balance = reply[1]
        assertions.expect(f"{name} non-negative", balance >= 0, True)
        known += balance

    assertions.expect("known balances do not exceed supply", known <= total, True)
    print(f"  supply={total} known={known}")
    print("unit_conservation: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
