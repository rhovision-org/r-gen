#!/usr/bin/env python3
"""Measure rendered and minified term sizes against the node's limits."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from minify_rho import minify  # noqa: E402

RAW_LIMIT = 57_344
MIN_LIMIT = 65_536


def measure() -> dict:
    rows = {}
    for directory in (ROOT / "contracts" / "build" / "deploy", ROOT / ".devnet" / "rendered"):
        for path in sorted(directory.glob("*.rho")):
            text = path.read_text()
            rows[str(path.relative_to(ROOT))] = {
                "raw": len(text.encode()),
                "minified": len(minify(text).encode()),
            }
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    rows = measure()
    bad = []
    for name, row in rows.items():
        if row["raw"] > RAW_LIMIT:
            bad.append(f"{name}: raw {row['raw']} > {RAW_LIMIT}")
        if row["minified"] > MIN_LIMIT:
            bad.append(f"{name}: minified {row['minified']} > {MIN_LIMIT}")
    if args.write:
        (ROOT / "contracts" / "measure.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(f"measure: wrote {len(rows)} row(s)")
    for name, row in rows.items():
        print(f"{name}: raw={row['raw']} minified={row['minified']}")
    if bad:
        for item in bad:
            print(f"measure: {item}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
