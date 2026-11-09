#!/usr/bin/env python3
"""The azoth bridge suite: the bundle offline, and the full claim on a devnet.

The offline half always runs, because it needs no node. The live half runs when a devnet
answers; without one the suite reports ``live: not run`` and still exits zero, so
``unit-all`` does not throw away the offline result.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import azoth_claim  # noqa: E402
import deploy as node  # noqa: E402
import preflight  # noqa: E402

ARTIFACTS = ROOT / "harness" / "demo" / "artifacts" / "azoth"


def main() -> int:
    problems = azoth_claim.verify(ARTIFACTS)
    if problems:
        for problem in problems:
            print(f"unit_azoth: {problem}", file=sys.stderr)
        return 1
    print("unit_azoth: bundle verified")

    if not preflight.require_devnet("unit_azoth"):
        print("unit_azoth: ok (offline: pass; live: not run)")
        return 0
    if not node.keys_path().is_file():
        print(f"unit_azoth: ok (offline: pass; live: not run: no {node.keys_path()})")
        return 0

    record = azoth_claim.deploy(ARTIFACTS, approve=True)
    if record.get("status") == "not_run":
        print("unit_azoth: ok (offline: pass; live: not run)")
        return 0

    checks = {
        "claim status": record.get("claimStatus") == "validated",
        "K-Asset status": record.get("kassetStatus") == "approved",
        "quantity": record.get("quantity", {}).get("value") == 5,
        "verdict": record.get("verdict") == "valid",
        "anchors": len(record.get("anchors", [])) == 7,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print(f"unit_azoth: failed: {failed}", file=sys.stderr)
        return 1
    if azoth_claim.verify_deployment() != 0:
        return 1
    print("unit_azoth: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
