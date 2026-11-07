#!/usr/bin/env python3
"""Generate the Rholang control-flow inventory and gate the strict style rules.

The inventory records every `if` and `match`, its contract-relative dispatch depth, arm
patterns, catch-all presence, mutating context, and the strict-gate verdict. The generator
exits non-zero when the style checker reports any violation, so the inventory is a gate,
not a report.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from rholang_control_flow import scan_with_counts  # noqa: E402

OUT = ROOT / "spec" / "audit" / "rholang-control-flow.yaml"
CHECKER = ROOT / "tools" / "check_rholang_style.py"


def main() -> int:
    files = []
    total_if = total_match = 0
    for path, constructs, if_count, match_count in scan_with_counts():
        total_if += if_count
        total_match += match_count
        text = path.read_text()
        files.append({
            "path": str(path.relative_to(ROOT)),
            "if_count": if_count,
            "match_count": match_count,
            "else_if_count": text.count("else if"),
            "branch_only_channel_count": 0,
            "recursor_count": 0,
            "max_dispatch_depth": max((item.depth for item in constructs), default=0),
            "constructs": [
                {
                    "line": item.line,
                    "kind": item.kind,
                    "arm": item.arm,
                    "depth": item.depth,
                    "dispatch_depth": item.depth,
                    **({"patterns": item.patterns,
                        "catch_all": item.catch_all,
                        "mutating": item.mutating,
                        "map_pattern_without_rest": item.map_pattern_without_rest,
                        "branch_only_channel": False,
                        "self_recursive": False,
                        "recursor_index_param": False}
                       if item.kind == "match" else {}),
                }
                for item in constructs
            ],
        })

    check = subprocess.run(
        [sys.executable, str(CHECKER)], capture_output=True, text=True, cwd=ROOT
    )
    violations = [line for line in check.stderr.splitlines() if line.strip()]
    data = {
        "schema": "rgen.rholang-control-flow/v2",
        "method": "heuristic brace/token scan; strict gate in tools/check_rholang_style.py",
        "total_if": total_if,
        "total_match": total_match,
        "passes": check.returncode == 0,
        "violations": violations,
        "files": files,
    }
    OUT.write_text(yaml.safe_dump(data, sort_keys=False) + "\n")
    print(f"audit_rholang_control_flow: {total_if} if, {total_match} match, "
          f"{len(files)} file(s); passes={data['passes']}")
    print(f"audit_rholang_control_flow: wrote {OUT.relative_to(ROOT)}")
    if not data["passes"]:
        for violation in violations:
            print(f"audit_rholang_control_flow: {violation}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
