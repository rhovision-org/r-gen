#!/usr/bin/env python3
"""Check component catalogue, state-cell uniqueness and dependency cycles."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOGUE = ROOT / "contracts" / "components.json"


def main() -> int:
    data = json.loads(CATALOGUE.read_text())
    components = data["components"]
    errors: list[str] = []

    seen: dict[str, str] = {}
    for name, rec in components.items():
        file = ROOT / "contracts" / "build" / "deploy" / rec["file"]
        if not file.is_file():
            errors.append(f"{name}: missing {file.relative_to(ROOT)}")
        for cell in rec.get("state_cells", []):
            if cell in seen:
                errors.append(f"state cell {cell} used by {seen[cell]} and {name}")
            seen[cell] = name
        for dep in rec.get("depends_on", []):
            if dep not in components:
                errors.append(f"{name}: unknown dependency {dep}")

    visiting: set[str] = set()
    done: set[str] = set()

    def visit(name: str) -> None:
        if name in done:
            return
        if name in visiting:
            errors.append(f"dependency cycle at {name}")
            return
        visiting.add(name)
        for dep in components[name].get("depends_on", []):
            visit(dep)
        visiting.remove(name)
        done.add(name)

    for name in components:
        visit(name)

    if errors:
        for error in errors:
            print(f"check-arch: {error}", file=sys.stderr)
        return 1
    print(f"check-arch: {len(components)} components, {len(seen)} state cells, acyclic")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
