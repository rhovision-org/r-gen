#!/usr/bin/env python3
"""Check that every arm named in spec/flows exists in a deploy term."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLOWS = ROOT / "spec" / "flows"
SOURCE = "\n".join(p.read_text() for p in (ROOT / "contracts" / "src" / "deploy").glob("*.rho"))


def main() -> int:
    errors = []
    count = 0
    for path in sorted(FLOWS.glob("*.yaml")):
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            if "arm:" not in line:
                continue
            arm = line.split("arm:", 1)[1].strip().strip("'\"")
            match = re.match(r'([A-Za-z0-9_]+)@"([^"]+)"', arm)
            if not match:
                errors.append(f"{path.name}:{lineno}: bad arm {arm}")
                continue
            count += 1
            contract, message = match.groups()
            if f'@"{message}"' not in SOURCE:
                errors.append(f"{path.name}:{lineno}: {contract} has no arm {message}")
    if errors:
        for error in errors:
            print(f"check-flows: {error}", file=sys.stderr)
        return 1
    print(f"check-flows: {count} arm(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
