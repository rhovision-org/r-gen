"""Load `spec/vectors/core.tsv` and tie suite outcomes to emitted rows.

The corpus is a finite tie: a `proved-conformance` claim is made only for a row that is
both emitted by Lean and asserted by a suite here. The expected vocabulary is deliberately
small:

* `some` — a `(true, ...)` reply
* `none` — a `(false, ...)` reply or a refused call
* `reject` — a refused call (same as `none` for assertions)
* `not-wf` — a non-`some` reply
* any other value — an equality check on the reply's second element
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "spec" / "vectors" / "core.tsv"


def rows(primitive: str | None = None) -> dict[str, dict[str, str]]:
    with CORPUS.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        data = {row["case_id"]: row for row in reader}
    if primitive is None:
        return data
    return {key: row for key, row in data.items() if row["primitive"] == primitive}


def is_ok(actual) -> bool:
    return isinstance(actual, tuple) and bool(actual) and actual[0] is True


def matches(expected: str, actual) -> bool:
    if expected in {"none", "reject"}:
        return not is_ok(actual)
    if expected == "some":
        return is_ok(actual)
    if expected == "not-wf":
        return not is_ok(actual)
    if is_ok(actual) and len(actual) > 1:
        return actual[1] == expected
    return False


def assert_row(case_id: str, actual, primitive: str | None = None) -> None:
    table = rows(primitive)
    if case_id not in table:
        raise AssertionError(f"corpus: no row {case_id}")
    expected = table[case_id]["expected"]
    if not matches(expected, actual):
        raise AssertionError(
            f"corpus {case_id}: expected {expected!r}, got {actual!r} "
            f"({table[case_id]['lean_decl']})")


def row_count(primitive: str | None = None) -> int:
    return len(rows(primitive))
