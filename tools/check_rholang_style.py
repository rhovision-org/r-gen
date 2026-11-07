#!/usr/bin/env python3
"""Enforce the Rholang match-first style.

Hard failures:

* a `match` in a mutating arm (a contract that consumes a cell) with no catch-all arm
  (`_`, a lone binder, or a total tuple bind);
* `@` inside a match pattern (a parse error in Rholang);
* a map pattern without `..._` when the match target is a `.get(...)` or a state map.

Warnings: deep `if`/`else if` chains, deep match nesting, duplicate verdict/outcome
tables, and repeated refusal strings. This is a heuristic scanner, not a parser; the
behavioral suites remain the gate.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from rholang_control_flow import scan_with_counts  # noqa: E402

def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    files = scan_with_counts()
    verdict_files: set[str] = set()
    outcome_files: set[str] = set()

    for path, constructs, if_count, match_count in files:
        rel = str(path.relative_to(ROOT))
        text = path.read_text()
        if '"valid"' in text and '"invalid"' in text:
            verdict_files.add(rel)
        if '"uphold"' in text and '"revoke"' in text:
            outcome_files.add(rel)
        for item in constructs:
            if item.kind != "match":
                continue
            if item.depth > 4:
                warnings.append(f"{item.file}:{item.line}: match depth {item.depth} > 4")
            for pattern in item.patterns:
                if "@" in pattern:
                    errors.append(f"{item.file}:{item.line}: '@' in match pattern: {pattern}")
            if item.mutating and not item.catch_all:
                errors.append(
                    f"{item.file}:{item.line}: mutating match has no catch-all arm"
                )
            target = item.text.split("{", 1)[0]
            if (".get(" in target or "get(\"" in target) and item.map_pattern_without_rest:
                errors.append(
                    f"{item.file}:{item.line}: map pattern on a .get target lacks '..._'"
                )
        if text.count("else if") > 2:
            warnings.append(f"{rel}: {text.count('else if')} 'else if' branches")
        if if_count and match_count == 0 and if_count > 4:
            warnings.append(f"{rel}: {if_count} if, no match; consider match dispatch")

    if len(verdict_files) > 1:
        warnings.append("verdict table appears in more than one file: "
                        + ", ".join(sorted(verdict_files)))
    if len(outcome_files) > 1:
        warnings.append("outcome table appears in more than one file: "
                        + ", ".join(sorted(outcome_files)))

    for warning in warnings:
        print(f"rholang-style: warning: {warning}")
    if errors:
        for error in errors:
            print(f"rholang-style: {error}", file=sys.stderr)
        return 1
    print(f"check_rholang_style: {sum(f[2] for f in files)} if, "
          f"{sum(f[3] for f in files)} match, {len(files)} file(s); "
          f"{len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
