#!/usr/bin/env python3
"""Dispute bonds, revocation and net-earned slashing."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import preflight


def main() -> int:
    if not preflight.require_devnet("unit_dispute"):
        return 2
    print("unit_dispute: not run — bond funding and slashing are the next phase",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
