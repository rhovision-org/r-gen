#!/usr/bin/env python3
"""Validate the multi-agent HAZOP run artifacts.

This is a structural gate, not a substitute for review. It requires:

* a run manifest with a blind-agent roster and input hashes;
* at least one workflow row for every workflow/cross-node node;
* the required evidence fields on every row;
* a two-source rule for every S1/S2 row (two authors or an adjudication entry);
* every evidence path to exist in the tree;
* every adjudication decision to reference an existing row.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / "spec" / "hazop" / "runs" / "2026-11-07"

WORKFLOW_NODES = {
    "wf-onboard",
    "wf-propose-claim",
    "wf-validate-mint",
    "wf-dispute-decide-execute",
    "wf-closeout-provenance",
    "wf-recovery",
    "xnode-authority",
    "xnode-registry",
    "xnode-time",
}
ROW_FIELDS = {
    "id", "node", "guide_word", "parameter", "deviation", "cause", "consequence",
    "safeguard", "safeguard_status", "severity", "likelihood", "evidence",
    "trigger", "falsifier", "confidence", "authors", "finding", "disposition",
}
SAFEGUARDS = {"holds", "partial", "none"}
SEVERITY = {"S1", "S2", "S3", "S4"}
LIKELIHOOD = {"A", "B", "C", "D"}
DISPOSITIONS = {"open", "fixed", "accepted", "accept-risk", "rejected"}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    manifest_path = RUN / "manifest.yaml"
    workflow_path = RUN / "workflow.yaml"
    adjudication_path = RUN / "adjudication.yaml"
    for path in (manifest_path, workflow_path, adjudication_path):
        if not path.is_file():
            fail(errors, f"missing {path.relative_to(ROOT)}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    manifest = yaml.safe_load(manifest_path.read_text()) or {}
    workflow = yaml.safe_load(workflow_path.read_text()) or {}
    adjudication = yaml.safe_load(adjudication_path.read_text()) or {}

    if manifest.get("schema") != "rgen.hazop-run/v1":
        fail(errors, "manifest: wrong schema")
    if not manifest.get("agents") or len(manifest["agents"]) < 3:
        fail(errors, "manifest: fewer than three blind agents")
    if not manifest.get("inputs_sha256"):
        fail(errors, "manifest: missing input hashes")

    rows = workflow.get("rows") or []
    if not rows:
        fail(errors, "workflow: no rows")
    seen_nodes: set[str] = set()
    row_ids: set[str] = set()
    for index, row in enumerate(rows):
        label = row.get("id", f"row[{index}]")
        missing = ROW_FIELDS - set(row)
        if missing:
            fail(errors, f"{label}: missing fields {sorted(missing)}")
            continue
        row_ids.add(row["id"])
        seen_nodes.add(row["node"])
        if row["node"] not in WORKFLOW_NODES:
            fail(errors, f"{label}: unknown workflow node {row['node']}")
        if row["safeguard_status"] not in SAFEGUARDS:
            fail(errors, f"{label}: bad safeguard_status")
        if row["severity"] not in SEVERITY:
            fail(errors, f"{label}: bad severity")
        if row["likelihood"] not in LIKELIHOOD:
            fail(errors, f"{label}: bad likelihood")
        if row["disposition"] not in DISPOSITIONS:
            fail(errors, f"{label}: bad disposition")
        evidence = str(row["evidence"]).split(":")[0]
        if not (ROOT / evidence).exists():
            fail(errors, f"{label}: evidence path does not exist: {evidence}")

    missing_nodes = WORKFLOW_NODES - seen_nodes
    if missing_nodes:
        fail(errors, f"workflow: no row for {sorted(missing_nodes)}")

    decisions = adjudication.get("decisions") or []
    decided_rows = {d.get("row") for d in decisions}
    for row in rows:
        if row.get("severity") in {"S1", "S2"}:
            authors = row.get("authors") or []
            if len(set(authors)) < 2 and row.get("id") not in decided_rows:
                fail(errors, f"{row.get('id')}: S1/S2 row needs two authors or an adjudication entry")
    for decision in decisions:
        if decision.get("row") not in row_ids:
            fail(errors, f"adjudication: unknown row {decision.get('row')}")

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"check_hazop_runs: {len(rows)} row(s), {len(seen_nodes)} node(s), "
          f"{len(decisions)} adjudication decision(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
