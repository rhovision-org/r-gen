#!/usr/bin/env python3
"""Check the close-out ledger against the findings ledger.

A P0/P1 finding is closed only when `spec/audit/closeout.yaml` carries exactly one
terminal decision for it. A fixed row must name evidence that exists; a risk-accepted
row must carry a rationale, an owner and a future expiry. The checker also reports
fixed rows whose evidence is code-only, so the missing negative test is visible.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FINDINGS = ROOT / "spec/audit/findings.yaml"
CLOSEOUT = ROOT / "spec/audit/closeout.yaml"
TERMINAL = {"fixed", "risk-accepted", "narrowed-claim"}
FINDING_DECISION = {"fixed": "fixed", "accept-risk": "risk-accepted"}


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def ref_path(ref: str) -> Path:
    return ROOT / ref.split(":", 1)[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true",
                        help="fail on a fixed row without test/theorem/gate/doc evidence")
    parser.add_argument("--strict-s1", action="store_true",
                        help="fail on a fixed S1 row without test/theorem/gate/doc evidence")
    args = parser.parse_args()

    findings = {f["id"]: f for f in load(FINDINGS).get("findings", [])}
    closeout = load(CLOSEOUT)
    errors: list[str] = []
    warnings: list[str] = []

    if closeout.get("schema_version") != "rgen.closeout/v1":
        errors.append("closeout: bad schema_version")
    rows = closeout.get("items") or []
    seen: set[str] = set()
    for row in rows:
        rid = row.get("id")
        if not rid:
            errors.append("closeout: row without id")
            continue
        if rid in seen:
            errors.append(f"{rid}: duplicate close-out row")
        seen.add(rid)
        finding = findings.get(rid)
        if finding is None:
            errors.append(f"{rid}: no such finding")
            continue
        if finding.get("priority") not in {"P0", "P1"}:
            warnings.append(f"{rid}: close-out row for a {finding.get('priority')} finding")
        decision = row.get("decision")
        if decision not in TERMINAL:
            errors.append(f"{rid}: non-terminal decision {decision!r}")
            continue
        expected = FINDING_DECISION.get(finding.get("disposition"))
        if expected and decision != expected:
            errors.append(f"{rid}: decision {decision!r} disagrees with disposition "
                          f"{finding.get('disposition')!r}")
        evidence = row.get("evidence") or []
        if not evidence:
            errors.append(f"{rid}: no evidence")
        kinds = set()
        for item in evidence:
            ref = item.get("ref")
            if not ref:
                errors.append(f"{rid}: evidence without ref")
                continue
            kinds.add(item.get("kind", "code"))
            if not ref_path(ref).exists():
                errors.append(f"{rid}: evidence does not exist: {ref}")
        if decision == "fixed":
            if not (kinds & {"test", "theorem", "gate", "doc"}):
                message = f"{rid}: fixed row has no test/theorem/gate/doc evidence"
                if args.strict or (args.strict_s1 and finding.get("severity") == "S1"):
                    errors.append(message)
                else:
                    warnings.append(message)
        if decision == "risk-accepted":
            for field in ("rationale", "owner", "expiry"):
                if not row.get(field):
                    errors.append(f"{rid}: risk-accepted row lacks {field}")
            expiry = row.get("expiry")
            if expiry:
                try:
                    when = dt.date.fromisoformat(str(expiry))
                except ValueError:
                    errors.append(f"{rid}: bad expiry {expiry!r}")
                else:
                    if when <= dt.date.today():
                        errors.append(f"{rid}: risk acceptance expired on {when}")
        if decision == "narrowed-claim" and not row.get("rationale"):
            errors.append(f"{rid}: narrowed-claim row lacks rationale")

    for fid, finding in findings.items():
        if finding.get("priority") in {"P0", "P1"} and fid not in seen:
            errors.append(f"{fid}: P0/P1 finding has no close-out row")

    for warning in warnings:
        print(f"check_closeout: warning: {warning}")
    for error in errors:
        print(f"check_closeout: {error}")
    if errors:
        print(f"check_closeout: {len(errors)} error(s)")
        return 1
    print(f"check_closeout: {len(seen)} row(s), {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
