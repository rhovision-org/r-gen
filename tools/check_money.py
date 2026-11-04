#!/usr/bin/env python3
"""Reject floating-point literals in contract sources."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLOAT = re.compile(r"(?<![\w.])\d+\.\d+(?![\w.])")


def main() -> int:
    bad = []
    for path in sorted((ROOT / "contracts" / "src").rglob("*.rho")):
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            if FLOAT.search(line):
                bad.append(f"{path.relative_to(ROOT)}:{lineno}")
    if bad:
        for item in bad:
            print(f"check-money: float literal at {item}", file=sys.stderr)
        return 1
    print("check-money: integer-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
