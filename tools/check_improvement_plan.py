#!/usr/bin/env python3
"""Check the risk/effort improvement portfolio.

`spec/audit/improvement-plan.yaml` schedules residual work after the P0/P1 close-out.
It must not duplicate a close-out decision, it must cover every S1 acceptance and every
partial improvement/rigor item, and a higher tier must not dominate a lower tier within
the same risk class.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "spec/audit/improvement-plan.yaml"
FINDINGS = ROOT / "spec/audit/findings.yaml"
WORKSHEET = ROOT / "spec/hazop/worksheet.yaml"
RUNS = ROOT / "spec/hazop/runs"
IMPROVEMENTS = ROOT / "spec/improvements/rholang.yaml"
RIGOR = ROOT / "spec/proofs/rigor.yaml"
CLOSEOUT = ROOT / "spec/audit/closeout.yaml"

CLASSES = {"live-risk", "assurance", "ops", "proof-debt", "supply-chain", "hygiene", "policy"}
STATUSES = {"proposed", "in-progress", "done", "dropped", "superseded"}
CONFIDENCE = {"high": 3, "medium": 2, "low": 1}


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def source_ids() -> dict[str, str]:
    """Map every ledger ID to its namespace."""
    ids: dict[str, str] = {}
    for finding in load(FINDINGS).get("findings", []):
        ids[finding["id"]] = "finding"
    for row in load(WORKSHEET).get("rows", []):
        ids[row["id"]] = "hazop"
    for run in sorted(RUNS.glob("*/workflow.yaml")):
        for row in load(run).get("rows", []):
            ids[row["id"]] = "run"
    for item in load(IMPROVEMENTS).get("items", []):
        ids[item["id"]] = "improvement"
    rigor = load(RIGOR)
    for key in ("roadmap", "divergences", "claims", "coverage"):
        for item in rigor.get(key, []) or []:
            if item.get("id"):
                ids[item["id"]] = "rigor"
    return ids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true",
                        help="fail on a dominated Tier 0/1 item")
    args = parser.parse_args(argv)

    plan = load(PLAN)
    findings = {f["id"]: f for f in load(FINDINGS).get("findings", [])}
    closeout = {r["id"]: r for r in load(CLOSEOUT).get("items", [])}
    improvements = {i["id"]: i for i in load(IMPROVEMENTS).get("items", [])}
    rigor = load(RIGOR)
    known = source_ids()

    errors: list[str] = []
    warnings: list[str] = []
    if plan.get("schema_version") != "rgen.improvement-plan/v1":
        errors.append("plan: bad schema_version")
    items = plan.get("items") or []
    if not items:
        errors.append("plan: no items")
    seen: set[str] = set()
    covered: set[str] = set()
    for item in items:
        iid = item.get("id", "")
        if not iid:
            errors.append("plan: item without id")
            continue
        if iid in seen:
            errors.append(f"{iid}: duplicate id")
        seen.add(iid)
        klass = item.get("class")
        if klass not in CLASSES:
            errors.append(f"{iid}: bad class {klass!r}")
        status = item.get("status")
        if status not in STATUSES:
            errors.append(f"{iid}: bad status {status!r}")
        confidence = item.get("confidence")
        if confidence not in CONFIDENCE:
            errors.append(f"{iid}: bad confidence {confidence!r}")
        risk = item.get("risk")
        effort = item.get("effort")
        if not isinstance(risk, int) or not 1 <= risk <= 5:
            errors.append(f"{iid}: risk must be an integer 1..5")
        if not isinstance(effort, int) or not 1 <= effort <= 5:
            errors.append(f"{iid}: effort must be an integer 1..5")
        tier = item.get("tier")
        if tier not in (0, 1, 2, 3):
            errors.append(f"{iid}: tier must be 0..3")
        for field in ("title", "action", "exit_criteria", "owner"):
            if not item.get(field):
                errors.append(f"{iid}: missing {field}")
        sources = item.get("sources") or []
        if not isinstance(sources, list):
            errors.append(f"{iid}: sources must be a list")
            sources = []
        for source in sources:
            if source not in known:
                errors.append(f"{iid}: unknown source {source!r}")
            covered.add(source)
        closeout_ref = item.get("closeout_ref")
        if closeout_ref:
            if closeout_ref not in findings:
                errors.append(f"{iid}: unknown closeout_ref {closeout_ref!r}")
            elif closeout_ref not in closeout:
                errors.append(f"{iid}: closeout_ref {closeout_ref} has no close-out row")
            covered.add(closeout_ref)
        if status == "done":
            evidence = item.get("evidence") or []
            if not evidence:
                errors.append(f"{iid}: done without evidence")
            for ev in evidence:
                ref = ev.get("ref") if isinstance(ev, dict) else None
                if not ref or not (ROOT / ref.split(":", 1)[0]).exists():
                    errors.append(f"{iid}: missing evidence {ref!r}")
        if status in {"dropped", "superseded"} and not item.get("note"):
            errors.append(f"{iid}: {status} without a note")
        if status == "superseded" and not item.get("superseded_by"):
            errors.append(f"{iid}: superseded without superseded_by")

    # Every S1 acceptance needs a scheduled or triaged item.
    for fid, finding in findings.items():
        if finding.get("severity") == "S1" and finding.get("disposition") == "accept-risk":
            if fid not in covered:
                errors.append(f"{fid}: S1 acceptance is not named in the plan")

    # Every accept-risk finding needs an item.
    for fid, finding in findings.items():
        if finding.get("disposition") == "accept-risk" and fid not in covered:
            errors.append(f"{fid}: accept-risk finding is not named in the plan")

    # Every partial RR/LR needs an item.
    for rid, item in improvements.items():
        if item.get("status") == "partial" and rid not in covered:
            errors.append(f"{rid}: partial improvement is not named in the plan")
    for item in rigor.get("roadmap", []) or []:
        if item.get("status") == "partial" and item.get("id") not in covered:
            errors.append(f"{item.get('id')}: partial roadmap item is not named in the plan")

    # Class-aware frontier: a lower tier must not be dominated by a higher tier.
    for item in items:
        if item.get("tier") not in (0, 1):
            continue
        for other in items:
            if other is item or other.get("tier", 99) <= item.get("tier", 99):
                continue
            if other.get("class") != item.get("class"):
                continue
            if (other.get("risk", 0) >= item.get("risk", 0)
                    and other.get("effort", 99) <= item.get("effort", 99)
                    and CONFIDENCE[other.get("confidence", "low")]
                    >= CONFIDENCE[item.get("confidence", "low")]):
                message = (f"{item['id']}: Tier {item['tier']} is dominated by "
                           f"Tier {other['tier']} {other['id']}")
                (errors if args.strict else warnings).append(message)

    # Expiring S1 acceptance with no scheduled item.
    today = dt.date.today()
    for fid, finding in findings.items():
        if finding.get("severity") == "S1" and finding.get("disposition") == "accept-risk":
            expiry = finding.get("expiry")
            if not expiry:
                continue
            try:
                when = dt.date.fromisoformat(str(expiry))
            except ValueError:
                errors.append(f"{fid}: bad expiry {expiry!r}")
                continue
            if (when - today).days <= 90:
                scheduled = [i for i in items if i.get("tier") in (0, 1, 2)
                             and (fid in (i.get("sources") or [])
                                  or i.get("closeout_ref") == fid)]
                if not scheduled:
                    warnings.append(f"{fid}: S1 acceptance expires within 90 days with no Tier 0-2 item")

    for warning in warnings:
        print(f"check_improvement_plan: warning: {warning}")
    for error in errors:
        print(f"check_improvement_plan: {error}")
    if errors:
        print(f"check_improvement_plan: {len(errors)} error(s)")
        return 1
    print(f"check_improvement_plan: {len(items)} item(s), {len(seen)} unique, "
          f"{len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
