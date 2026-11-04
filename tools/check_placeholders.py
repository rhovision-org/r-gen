#!/usr/bin/env python3
"""Reject placeholders outside the installer's allowlist."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {
    "__ROOT_URI__",
    "__IDENTITY_DIRECTORY_URI__",
    "__CREDENTIAL_FACTORY_URI__",
    "__ORACLE_FACTORY_URI__",
    "__VALUE_PROPOSITION_FACTORY_URI__",
}
PATTERN = re.compile(r"__[A-Z0-9_]+__")


def main() -> int:
    bad = []
    for path in sorted((ROOT / "contracts" / "src").rglob("*.rho")):
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            for match in PATTERN.findall(line):
                if match not in ALLOWED:
                    bad.append(f"{path.relative_to(ROOT)}:{lineno}: {match}")
    if bad:
        for item in bad:
            print(f"check-placeholders: {item}", file=sys.stderr)
        return 1
    print(f"check-placeholders: {len(ALLOWED)} allowed placeholder(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
