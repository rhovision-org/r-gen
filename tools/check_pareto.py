#!/usr/bin/env python3
"""Check the Pareto core manifest.

`spec/pareto.yaml` is the authoritative minimal set: seven Rholang terms, the catalogue
cell boundary, the essential Lean modules/theorems, and the paper-linked documentation.
This gate verifies existence, the theorem vocabulary in `RGen/Pareto.lean`, and the
minimum page-cited density per primitive page.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "spec" / "pareto.yaml"
LEAN = ROOT / "spec" / "lean" / "RGen"
CATALOGUE = ROOT / "contracts" / "components.json"
CITATION = re.compile(r"@[a-z][a-z0-9]+ p\.\d+")
DECL = re.compile(r"\b(?:theorem|lemma|def)\s+([A-Za-z0-9_']+)")


def parse(path: Path) -> dict:
    data: dict[str, object] = {}
    current: str | None = None
    current_doc: dict[str, str] | None = None
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" "):
            key, _, value = line.partition(":")
            current = key.strip()
            value = value.strip()
            if value:
                data[current] = value
            else:
                data[current] = []
            current_doc = None
            continue
        stripped = line.strip()
        if current is None:
            raise ValueError(f"list item before key: {raw!r}")
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if ":" in item and current == "docs":
                k, _, v = item.partition(":")
                current_doc = {k.strip(): v.strip()}
                data[current].append(current_doc)
            else:
                if current == "docs":
                    raise ValueError(f"bad docs item: {raw!r}")
                data[current].append(item.strip('"'))
            continue
        if current_doc is not None and ":" in stripped:
            k, _, v = stripped.partition(":")
            current_doc[k.strip()] = v.strip()
            continue
        raise ValueError(f"cannot parse manifest line: {raw!r}")
    return data


def lean_decls() -> set[str]:
    names: set[str] = set()
    for path in sorted(LEAN.rglob("*.lean")):
        if ".lake" in path.parts:
            continue
        names.update(DECL.findall(path.read_text()))
    return names


def main() -> int:
    try:
        data = parse(MANIFEST)
    except (OSError, ValueError) as exc:
        print(f"check_pareto: {exc}", file=sys.stderr)
        return 2

    errors: list[str] = []
    for term in data.get("terms", []):
        if not (ROOT / term).is_file():
            errors.append(f"missing core term {term}")

    catalogue = json.loads(CATALOGUE.read_text())
    cells = set(data.get("cells", []))
    declared_cells = set(catalogue.get("serialization_points", {}))
    for component in catalogue["components"].values():
        declared_cells.update(component.get("state_cells", []))
    missing = cells - declared_cells
    if missing:
        errors.append(f"core cells not in catalogue: {sorted(missing)}")
    expected_components = int(data.get("components", 0))
    if len(catalogue["components"]) != expected_components:
        errors.append(
            f"catalogue has {len(catalogue['components'])} components, "
            f"manifest says {expected_components}")

    for module in data.get("lean_modules", []):
        if not (ROOT / module).is_file():
            errors.append(f"missing Lean module {module}")

    decls = lean_decls()
    pareto = (LEAN / "Pareto.lean").read_text()
    for theorem in data.get("theorems", []):
        short = theorem.rsplit(".", 1)[-1]
        if short not in decls:
            errors.append(f"theorem {theorem} not found in Lean sources")
        if f"#check {theorem}" not in pareto:
            errors.append(f"theorem {theorem} is not in RGen/Pareto.lean")

    for entry in data.get("docs", []):
        path = ROOT / entry["path"]
        if not path.is_file():
            errors.append(f"missing docs page {entry['path']}")
            continue
        count = len(CITATION.findall(path.read_text()))
        required = int(entry.get("citations", 0))
        if count < required:
            errors.append(
                f"{entry['path']}: {count} page citation(s), need {required}")

    if errors:
        for error in errors:
            print(f"check_pareto: {error}", file=sys.stderr)
        print(f"check_pareto: {len(errors)} error(s)", file=sys.stderr)
        return 1

    print(f"check_pareto: {len(data.get('terms', []))} term(s), "
          f"{len(data.get('cells', []))} cell(s), "
          f"{len(data.get('theorems', []))} theorem(s), "
          f"{len(data.get('docs', []))} docs page(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
