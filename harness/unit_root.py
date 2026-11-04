#!/usr/bin/env python3
"""Root directory, installer gate and duplicate registration."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import actors
import assertions
import preflight
from terms import Raw


def main() -> int:
    if not preflight.require_devnet("unit_root"):
        return 2

    root = assertions.root_uri()
    assertions.expect("root URI", root.startswith("rho:id:"), True)

    reply = assertions.call(root, "resolve", ["component:root", 1], deployer=False)
    assertions.expect_ok("resolve root", reply)
    assertions.expect("root is itself", reply[1], root)

    reply = assertions.call(root, "resolve", ["component:missing", 1], deployer=False)
    assertions.expect_refusal("unknown component", reply, "unknown component")

    reply = assertions.call(root, "register",
                            ["component:duplicate", "rho:id:x", 1, "test", Raw("*dId")])
    assertions.expect_ok("installer register", reply)
    reply = assertions.call(root, "register",
                            ["component:duplicate", "rho:id:x", 1, "test", Raw("*dId")])
    assertions.expect_refusal("duplicate register", reply, "duplicate")

    actors.ensure_vault("admin1")
    reply = assertions.call(root, "register",
                            ["component:spoof", "rho:id:x", 1, "test", Raw("*dId")],
                            key="admin1")
    assertions.expect_refusal("non-installer register", reply, "not installer")

    print("unit_root: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
