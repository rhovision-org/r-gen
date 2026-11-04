#!/usr/bin/env python3
"""Fail if the Pareto core references an extension concern.

The core may not mention tokenisation, payment, risk, panels, admin or handles. Comments
are stripped before scanning so the rationale headers do not trip the gate.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATHS = sorted((ROOT / "contracts" / "src").rglob("*.rho"))
FORBIDDEN = re.compile(
    r"\b(token|tokens|KAT|mint|mintForKAsset|risk|riskScore|payments|PaymentBook|"
    r"admin|AdminGuard|panel|panels|handles)\b")
FORBIDDEN_URIS = re.compile(
    r"component:(token|risk-book|payments|admin)")


def strip_comment(line: str) -> str:
    in_string = False
    escaped = False
    out = []
    i = 0
    while i < len(line):
        ch = line[i]
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
                out.append(ch)
            elif ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                break
            else:
                out.append(ch)
        i += 1
    return "".join(out)


def main() -> int:
    bad = []
    for path in PATHS:
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            code = strip_comment(line)
            for match in FORBIDDEN.finditer(code):
                bad.append(f"{path.relative_to(ROOT)}:{lineno}: {match.group(0)}")
            if FORBIDDEN_URIS.search(code):
                bad.append(f"{path.relative_to(ROOT)}:{lineno}: extension URI")
    if bad:
        for item in bad:
            print(f"check-core-boundary: {item}", file=sys.stderr)
        return 1
    print(f"check-core-boundary: {len(PATHS)} file(s), no extension references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
