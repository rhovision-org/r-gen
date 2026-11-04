#!/usr/bin/env python3
"""Check that every docs page is listed in SUMMARY.md."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs" / "src"


def main() -> int:
    summary = DOCS / "SUMMARY.md"
    if not summary.is_file():
        print("check-docs: missing docs/src/SUMMARY.md", file=sys.stderr)
        return 1
    listed = set()
    for line in summary.read_text().splitlines():
        if "](" in line and ")" in line:
            listed.add(line.split("](", 1)[1].split(")", 1)[0])
    missing = []
    for path in DOCS.rglob("*.md"):
        rel = str(path.relative_to(DOCS))
        if rel == "SUMMARY.md":
            continue
        if rel not in listed:
            missing.append(rel)
    if missing:
        for item in missing:
            print(f"check-docs: not in SUMMARY.md: {item}", file=sys.stderr)
        return 1
    print(f"check-docs: {len(listed)} page(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
