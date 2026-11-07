#!/usr/bin/env python3
"""Enforce the Rholang match-first style.

Every rule is a hard failure; there is no warning channel:

* dispatch depth > 2 (enclosing if/match inside the current contract);
* any `else if` ladder;
* a branch-only private channel that sends a boolean and immediately branches on it;
* a map pattern without `..._`;
* a mutating match with no catch-all (`_`, lone binder, or total tuple bind);
* `@` in a match pattern (a parse error in Rholang);
* a duplicate verdict or outcome table;
* index recursion (`if (i >= ...length())`, `.nth(i)`).

This is a heuristic brace/token scanner, not a parser. The behavioral suites and the red
team remain the gate.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from rholang_control_flow import scan_with_counts  # noqa: E402


def branch_only_channel(lines: list[str], start: int) -> str | None:
    match = re.match(r"\s*new\s+([A-Za-z_][A-Za-z0-9_']*)\s+in\b", lines[start])
    if not match:
        return None
    name = match.group(1)
    window = "\n".join(lines[start:start + 40])
    sends_bool = re.search(rf"\b{name}!\((true|false)\)", window)
    receives = re.search(rf"for\s*\(@\w+\s*<-\s*{name}\)", window)
    if sends_bool and receives:
        return name
    return None


def main() -> int:
    errors: list[str] = []
    files = scan_with_counts()
    verdict_files: set[str] = set()
    outcome_files: set[str] = set()

    for path, constructs, if_count, match_count in files:
        rel = str(path.relative_to(ROOT))
        text = path.read_text()
        lines = text.splitlines()
        if '"valid"' in text and '"invalid"' in text:
            verdict_files.add(rel)
        if '"uphold"' in text and '"revoke"' in text:
            outcome_files.add(rel)
        for item in constructs:
            if item.depth > 2:
                errors.append(
                    f"{item.file}:{item.line}: {item.kind} dispatch depth {item.depth} > 2"
                )
            if item.kind != "match":
                continue
            for pattern in item.patterns:
                if "@" in pattern:
                    errors.append(
                        f"{item.file}:{item.line}: '@' in match pattern: {pattern}"
                    )
            if item.mutating and not item.catch_all:
                errors.append(
                    f"{item.file}:{item.line}: mutating match has no catch-all arm"
                )
            if item.map_pattern_without_rest:
                errors.append(
                    f"{item.file}:{item.line}: map pattern lacks '..._'"
                )
        if "else if" in text:
            errors.append(f"{rel}: 'else if' ladder; use a tuple match")
        if re.search(r"\bif\s*\([^)]*(>=|>)\s*[^)]*\.length\(\)", text) or ".nth(" in text:
            errors.append(f"{rel}: index recursion; use list-pattern recursion")
        for index, line in enumerate(lines):
            name = branch_only_channel(lines, index)
            if name:
                errors.append(
                    f"{rel}:{index + 1}: branch-only channel {name}; return the expression"
                )

    if len(verdict_files) > 1:
        errors.append("verdict table appears in more than one file: "
                      + ", ".join(sorted(verdict_files)))
    if len(outcome_files) > 1:
        errors.append("outcome table appears in more than one file: "
                      + ", ".join(sorted(outcome_files)))

    if errors:
        for error in errors:
            print(f"rholang-style: {error}", file=sys.stderr)
        return 1
    print(f"check_rholang_style: {sum(f[2] for f in files)} if, "
          f"{sum(f[3] for f in files)} match, {len(files)} file(s); 0 error(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
