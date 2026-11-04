#!/usr/bin/env python3
"""r-cash escrow funding, release and refusal without a decision."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import preflight


def main() -> int:
    if not preflight.require_devnet("unit_payments"):
        return 2
    print("unit_payments: not run — the funded escrow scenario is the next phase",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
