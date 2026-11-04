#!/usr/bin/env python3
"""Check the deployed arms against the Lean flow manifest.

`spec/flows/core.yaml` maps every deployed arm to a Lean declaration and a
status. This gate enforces:

* every arm parsed from `contracts/src/**/*.rho` appears in the manifest;
* the status is one of `proved-model`, `proved-conformance`, `owed`, `open`;
* `proved-model` / `proved-conformance` entries name a Lean declaration that
  exists in `spec/lean/`;
* `proved-conformance` entries also appear in `spec/vectors/core.tsv`;
* `owed` / `open` entries carry a `note` explaining the gap.

The manifest is a deliberately small YAML subset: a list of flat `key: value`
maps. No external YAML dependency is needed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "spec" / "flows" / "core.yaml"
LEAN_DIR = ROOT / "spec" / "lean" / "RGen"
CORPUS = ROOT / "spec" / "vectors" / "core.tsv"
CONTRACT = re.compile(r'contract\s+([A-Za-z0-9_]+)\s*\(\s*@"([A-Za-z0-9_]+)"')
STATUSES = {"proved-model", "proved-conformance", "owed", "open"}
DECL = re.compile(r"\b(?:theorem|lemma|def)\s+([A-Za-z0-9_']+)")


def parse_manifest(path: Path) -> list[dict[str, str]]:
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
            raise ValueError(f"cannot parse manifest line: {raw!r}")
        key, value = line.split(":", 1)
        current[key.strip()] = value.strip().strip('"').strip("'")
    if current is not None:
        entries.append(current)
    return entries


def deployed_arms() -> set[tuple[str, str, str]]:
    arms: set[tuple[str, str, str]] = set()
    for path in sorted((ROOT / "contracts" / "src").rglob("*.rho")):
        text = path.read_text()
        for match in CONTRACT.finditer(text):
            arms.add((str(path.relative_to(ROOT)), match.group(1), match.group(2)))
    return arms


def lean_declarations() -> set[str]:
    names: set[str] = set()
    for path in sorted(LEAN_DIR.rglob("*.lean")):
        if ".lake" in path.parts:
            continue
        names.update(DECL.findall(path.read_text()))
    return names


def corpus_decls() -> set[str]:
    if not CORPUS.is_file():
        return set()
    lines = CORPUS.read_text().splitlines()
    if not lines:
        return set()
    header = lines[0].split("\t")
    if "lean_decl" not in header:
        return set()
    index = header.index("lean_decl")
    return {line.split("\t")[index] for line in lines[1:] if line.strip()}


def main() -> int:
    errors: list[str] = []
    try:
        entries = parse_manifest(MANIFEST)
    except (OSError, ValueError) as exc:
        print(f"check-flows: {exc}", file=sys.stderr)
        return 2

    decls = lean_declarations()
    corpus = corpus_decls()
    deployed = deployed_arms()
    seen: set[tuple[str, str, str]] = set()

    for entry in entries:
        for field in ("file", "contract", "arm", "lean", "status"):
            if not entry.get(field):
                errors.append(f"manifest entry missing {field}: {entry}")
                continue
        status = entry.get("status", "")
        if status not in STATUSES:
            errors.append(f"bad status {status!r} for {entry.get('file')}:{entry.get('arm')}")
            continue
        key = (entry.get("file", ""), entry.get("contract", ""), entry.get("arm", ""))
        if key in seen:
            errors.append(f"duplicate manifest entry: {key}")
        seen.add(key)
        if key not in deployed:
            errors.append(f"manifest entry is not deployed: {key}")
        lean = entry.get("lean", "-")
        if status in {"proved-model", "proved-conformance"}:
            if lean == "-":
                errors.append(f"{key}: {status} without a Lean declaration")
            else:
                short = lean.rsplit(".", 1)[-1]
                if short not in decls:
                    errors.append(f"{key}: Lean declaration {lean} not found")
            if status == "proved-conformance" and lean not in corpus:
                errors.append(f"{key}: proved-conformance without a core.tsv row")
        if status in {"owed", "open"} and not entry.get("note"):
            errors.append(f"{key}: {status} without a note")
        for field in ("transition", "authority", "classification"):
            value = entry.get(field)
            if value and value != "-":
                short = value.rsplit(".", 1)[-1]
                if short not in decls:
                    errors.append(f"{key}: {field} {value} not found")

    for key in sorted(deployed - seen):
        errors.append(f"deployed arm missing from manifest: {key}")

    if errors:
        for error in errors:
            print(f"check-flows: {error}", file=sys.stderr)
        print(f"check-flows: {len(errors)} error(s)", file=sys.stderr)
        return 1

    counts = {status: 0 for status in STATUSES}
    for entry in entries:
        counts[entry["status"]] += 1
    print(f"check-flows: {len(entries)} arm(s) mapped "
          f"({counts['proved-model']} proved-model, "
          f"{counts['proved-conformance']} proved-conformance, "
          f"{counts['owed']} owed, {counts['open']} open)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
