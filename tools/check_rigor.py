#!/usr/bin/env python3
"""Rigor ledger gate: no unstatused divergence or invariant gap.

A divergence is `resolved` (model and code agree), `justified` (a documented
abstraction with no authority impact), or `material` (needs a scheduled closure).
Every material divergence must name an improvement-plan item.
"""

from __future__ import annotations

import sys

import yaml

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RIGOR = ROOT / "spec/proofs/rigor.yaml"
PLAN = ROOT / "spec/audit/improvement-plan.yaml"

DIV_STATUS = {"resolved", "justified", "material"}
COVERAGE_STATUS = {"covered", "proved", "partial", "proved-but-narrower"}


def main() -> int:
    rigor = yaml.safe_load(RIGOR.read_text())
    plan = yaml.safe_load(PLAN.read_text())
    items = {item["id"] for item in plan.get("items", [])}
    errors: list[str] = []
    for div in rigor.get("divergences", []) or []:
        did = div.get("id", "?")
        if div.get("status") not in DIV_STATUS:
            errors.append(f"{did}: bad or missing status {div.get('status')!r}")
            continue
        if not div.get("justification"):
            errors.append(f"{did}: missing justification")
        if div["status"] == "material" and div.get("closure") not in items:
            errors.append(f"{did}: material divergence has no valid closure item")
    for cov in rigor.get("coverage", []) or []:
        cid = cov.get("id", "?")
        if cov.get("status") not in COVERAGE_STATUS:
            errors.append(f"{cid}: bad or missing coverage status {cov.get('status')!r}")
    for claim in rigor.get("claims", []) or []:
        if claim.get("verdict") == "proved-but-narrower" and not (claim.get("note") or claim.get("finding")):
            errors.append(f"{claim.get('id')}: proved-but-narrower without a note or finding")
    for error in errors:
        print(f"check_rigor: {error}")
    if errors:
        print(f"check_rigor: {len(errors)} error(s)")
        return 1
    print(f"check_rigor: {len(rigor.get('divergences', []) or [])} divergence(s), "
          f"{len(rigor.get('coverage', []) or [])} coverage row(s), "
          f"{len(rigor.get('claims', []) or [])} claim(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
