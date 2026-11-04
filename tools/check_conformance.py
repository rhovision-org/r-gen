#!/usr/bin/env python3
"""Check the `proved-conformance` evidence bundle.

`proved-conformance` is not a refinement claim. It means:

* the arm has a `proved-model` theorem;
* the theorem has an emitted row in `spec/vectors/core.tsv`; and
* a deployed harness suite asserts the same row (the manifest `suite` field).

This gate reports the current promotion count and rejects any partial bundle.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "spec" / "flows" / "core.yaml"
CORPUS = ROOT / "spec" / "vectors" / "core.tsv"


def parse_manifest() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw in MANIFEST.read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("- "):
            if current is not None:
                entries.append(current)
            current = {}
            line = line[2:]
        if current is None or ":" not in line:
            continue
        key, value = line.split(":", 1)
        current[key.strip()] = value.strip().strip('"').strip("'")
    if current is not None:
        entries.append(current)
    return entries


def corpus_rows() -> set[str]:
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
    entries = parse_manifest()
    rows = corpus_rows()
    errors: list[str] = []
    promoted = 0
    for entry in entries:
        if entry.get("status") != "proved-conformance":
            continue
        promoted += 1
        key = f"{entry.get('file')}:{entry.get('contract')}@{entry.get('arm')}"
        lean = entry.get("lean", "-")
        if lean == "-":
            errors.append(f"{key}: proved-conformance without a Lean declaration")
        elif lean not in rows:
            errors.append(f"{key}: proved-conformance without a core.tsv row for {lean}")
        if not entry.get("suite"):
            errors.append(f"{key}: proved-conformance without a deployed suite assertion")
    if errors:
        for error in errors:
            print(f"check_conformance: {error}", file=sys.stderr)
        print(f"check_conformance: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"check_conformance: {promoted} promoted arm(s), "
          f"{len(rows)} emitted vector row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
