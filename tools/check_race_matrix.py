#!/usr/bin/env python3
"""Check the arm-pair race matrix against the Lean sources.

Every entry declares a cell, two arms, a class, and a Lean theorem. This gate verifies the
class vocabulary, uniqueness of the pair, and that the theorem exists in `spec/lean`.
It is a tie, not a refinement: the matrix records the hand mapping from the deployed arms
to the Lean pair theorems.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MATRIX = ROOT / "spec" / "flows" / "races.yaml"
LEAN_DIR = ROOT / "spec" / "lean" / "RGen"
CLASSES = {"exclusive", "ordered", "independent"}
DECL = re.compile(r"\b(?:theorem|lemma|def)\s+([A-Za-z0-9_']+)")


def parse(path: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("- "):
            if current is not None:
                entries.append(current)
            current = {}
            line = line[2:]
        if current is None or ":" not in line:
            raise ValueError(f"cannot parse matrix line: {raw!r}")
        key, value = line.split(":", 1)
        current[key.strip()] = value.strip().strip('"').strip("'")
    if current is not None:
        entries.append(current)
    return entries


def declarations() -> set[str]:
    names: set[str] = set()
    for path in sorted(LEAN_DIR.rglob("*.lean")):
        if ".lake" in path.parts:
            continue
        names.update(DECL.findall(path.read_text()))
    return names


def main() -> int:
    try:
        entries = parse(MATRIX)
    except (OSError, ValueError) as exc:
        print(f"check_race_matrix: {exc}", file=sys.stderr)
        return 2

    decls = declarations()
    errors: list[str] = []
    seen: set[tuple[str, str, str, str]] = set()
    for entry in entries:
        cell = entry.get("cell", "")
        a, b, cls, theorem = (entry.get(k, "") for k in ("a", "b", "class", "theorem"))
        if not (cell and a and b and cls and theorem):
            errors.append(f"incomplete matrix entry: {entry}")
            continue
        if cls not in CLASSES:
            errors.append(f"{cell}:{a}/{b}: bad class {cls!r}")
        key = (cell, a, b, entry.get("case", ""))
        if key in seen:
            errors.append(f"duplicate pair {key}")
        seen.add(key)
        short = theorem.rsplit(".", 1)[-1]
        if short not in decls:
            errors.append(f"{cell}:{a}/{b}: theorem {theorem} not found")

    if errors:
        for error in errors:
            print(f"check_race_matrix: {error}", file=sys.stderr)
        print(f"check_race_matrix: {len(errors)} error(s)", file=sys.stderr)
        return 1

    counts: dict[str, int] = {cls: 0 for cls in CLASSES}
    for entry in entries:
        counts[entry["class"]] += 1
    print(f"check_race_matrix: {len(entries)} pair(s) "
          f"({counts['exclusive']} exclusive, {counts['ordered']} ordered, "
          f"{counts['independent']} independent)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
