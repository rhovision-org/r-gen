#!/usr/bin/env python3
"""Check that published contracts are bundled and no weakened bundle syntax is used."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BAD = re.compile(r"bundle0|bundle-")
RS = re.compile(r"(?<![A-Za-z0-9_])rs!\(([^,]+),")


def main() -> int:
    bad = []
    for path in sorted((ROOT / "contracts" / "src" / "deploy").glob("*.rho")):
        text = path.read_text()
        for lineno, line in enumerate(text.splitlines(), 1):
            if BAD.search(line):
                bad.append(f"{path.name}:{lineno}: weakened bundle")
            for target in RS.findall(line):
                if not target.strip().startswith("bundle+{*"):
                    bad.append(f"{path.name}:{lineno}: unbundled publish {target.strip()}")
    if bad:
        for item in bad:
            print(f"check-captures: {item}", file=sys.stderr)
        return 1
    print("check-captures: all publishes bundled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
