#!/usr/bin/env python3
"""Generate the Rholang control-flow inventory.

The inventory is heuristic: it records every `if` and `match` the scanner finds, the
enclosing contract line, approximate brace depth, arm patterns, catch-all presence, and
whether the match is in a mutating context. See `docs/src/reference/rholang-style.md`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from rholang_control_flow import scan_with_counts  # noqa: E402

OUT = ROOT / "spec" / "audit" / "rholang-control-flow.yaml"


def main() -> int:
    files = []
    total_if = total_match = 0
    for path, constructs, if_count, match_count in scan_with_counts():
        total_if += if_count
        total_match += match_count
        files.append({
            "path": str(path.relative_to(ROOT)),
            "if_count": if_count,
            "match_count": match_count,
            "max_depth": max((item.depth for item in constructs), default=0),
            "constructs": [
                {
                    "line": item.line,
                    "kind": item.kind,
                    "arm": item.arm,
                    "depth": item.depth,
                    **({"patterns": item.patterns,
                        "catch_all": item.catch_all,
                        "mutating": item.mutating,
                        "map_pattern_without_rest": item.map_pattern_without_rest}
                       if item.kind == "match" else {}),
                }
                for item in constructs
            ],
        })
    data = {
        "schema": "rgen.rholang-control-flow/v1",
        "method": "heuristic brace/token scan; not a parser",
        "total_if": total_if,
        "total_match": total_match,
        "files": files,
    }
    OUT.write_text(yaml.safe_dump(data, sort_keys=False) + "\n")
    print(f"audit_rholang_control_flow: {total_if} if, {total_match} match, {len(files)} file(s)")
    print(f"audit_rholang_control_flow: wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
