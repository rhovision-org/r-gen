#!/usr/bin/env python3
"""Generate or refresh `spec/vectors/core.tsv` from the Lean emitter.

The Lean table in `spec/lean/RGen/Emit.lean` is the source of truth. This tool
runs `lake exe emit` and either writes the file (`--write`) or reports whether
the checked-in file is current.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEAN = ROOT / "spec" / "lean"
TARGET = ROOT / "spec" / "vectors" / "core.tsv"


def emit() -> str:
    try:
        return subprocess.check_output(["lake", "exe", "emit"], cwd=LEAN, text=True)
    except FileNotFoundError:
        print("gen_vectors: `lake` not found in PATH", file=sys.stderr)
        raise SystemExit(2)
    except subprocess.CalledProcessError as exc:
        print(f"gen_vectors: Lean emitter failed ({exc.returncode})", file=sys.stderr)
        raise SystemExit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the emitted table")
    args = parser.parse_args()

    data = emit()
    rows = max(0, len(data.strip().splitlines()) - 1)
    if args.write:
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(data)
        print(f"gen_vectors: wrote {rows} row(s) to {TARGET.relative_to(ROOT)}")
        return 0

    current = TARGET.read_text() if TARGET.is_file() else ""
    if current != data:
        print("gen_vectors: core.tsv is stale; run tools/gen_vectors.py --write",
              file=sys.stderr)
        return 1
    print(f"gen_vectors: {rows} row(s) current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
