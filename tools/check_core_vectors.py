#!/usr/bin/env python3
"""Check that `spec/vectors/core.tsv` is exactly the Lean-emitted corpus.

The legacy `tools/check_vectors.py` checks the pre-Pareto risk/mint JSON
vectors; this tool checks the Lean conformance corpus only.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEAN = ROOT / "spec" / "lean"
TARGET = ROOT / "spec" / "vectors" / "core.tsv"
COLUMNS = ["case_id", "primitive", "arm", "input", "expected", "lean_decl"]


def main() -> int:
    try:
        emitted = subprocess.check_output(["lake", "exe", "emit"], cwd=LEAN, text=True)
    except FileNotFoundError:
        print("check_core_vectors: `lake` not found in PATH", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        print(f"check_core_vectors: Lean emitter failed ({exc.returncode})", file=sys.stderr)
        return 2

    if not TARGET.is_file():
        print(f"check_core_vectors: missing {TARGET.relative_to(ROOT)}", file=sys.stderr)
        return 1

    current = TARGET.read_text()
    if current != emitted:
        print("check_core_vectors: core.tsv differs from the Lean emitter", file=sys.stderr)
        cur = current.splitlines()
        new = emitted.splitlines()
        for index in range(max(len(cur), len(new))):
            left = cur[index] if index < len(cur) else "<missing>"
            right = new[index] if index < len(new) else "<missing>"
            if left != right:
                print(f"  line {index + 1}:", file=sys.stderr)
                print(f"    file:   {left}", file=sys.stderr)
                print(f"    lean:   {right}", file=sys.stderr)
                break
        return 1

    header = current.splitlines()[0].split("\t") if current else []
    if header != COLUMNS:
        print(f"check_core_vectors: bad header {header}", file=sys.stderr)
        return 1

    rows = max(0, len(current.strip().splitlines()) - 1)
    print(f"check_core_vectors: {rows} row(s) match the Lean emitter")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
