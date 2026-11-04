#!/usr/bin/env python3
"""Check that the suite runner and the harness agree."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "harness" / "run_suites.py"
MAKEFILE = ROOT / "Makefile"


def main() -> int:
    text = RUNNER.read_text()
    suites = re.findall(r'"([a-z-]+)":\s*"unit_([a-z_]+)\.py"', text)
    errors = []
    if not suites:
        errors.append("could not parse SUITES in harness/run_suites.py")
    make = MAKEFILE.read_text()
    for name, script in suites:
        path = ROOT / "harness" / f"unit_{script}.py"
        if not path.is_file():
            errors.append(f"missing {path.relative_to(ROOT)}")
        if f"unit-{name}:" not in make:
            errors.append(f"Makefile has no unit-{name} target")
    if errors:
        for error in errors:
            print(f"check-suites: {error}", file=sys.stderr)
        return 1
    print(f"check-suites: {len(suites)} suite(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
