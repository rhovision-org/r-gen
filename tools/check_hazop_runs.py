#!/usr/bin/env python3
"""Validate the multi-agent HAZOP run artifacts.

This is a structural gate, not a substitute for review. For every directory under
`spec/hazop/runs/` it requires:

* a run manifest with a blind-agent roster and input hashes;
* at least one workflow row for every node declared by that run;
* the required evidence fields on every row;
* a two-source rule for every S1/S2 row (two authors or an adjudication entry);
* every evidence path to exist in the tree;
* every cited finding to exist in `spec/audit/findings.yaml` (or the run manifest);
* every cited capability register id to exist in `spec/audit/capabilities.yaml`;
* every adjudication decision to reference an existing row.

The 2026-11-07 run predates the per-run `nodes`/`guide_words` fields, so the checker
falls back to the original workflow-node and guide-word sets.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "spec" / "hazop" / "runs"
FINDINGS = ROOT / "spec" / "audit" / "findings.yaml"
CAPABILITIES = ROOT / "spec" / "audit" / "capabilities.yaml"
REDTEAM = ROOT / "spec" / "audit" / "redteam.yaml"
REDTEAM_CAPABILITIES = ROOT / "spec" / "audit" / "redteam-capabilities.yaml"

DEFAULT_NODES = {
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
DEFAULT_GUIDE_WORDS = {
    "No/Not", "More", "Less", "As well as", "Part of", "Reverse", "Other than",
    "Late", "Early", "Before", "After", "Duplicate/Replay", "Stale",
    "Substitute/confused-deputy", "Partial commit",
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


def load_ids(path: Path, key: str, errors: list[str]) -> set[str]:
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError) as exc:
        fail(errors, f"{path.relative_to(ROOT)}: {exc}")
        return set()
    return {row.get("id") for row in data.get(key) or [] if row.get("id")}


def check_run(run: Path, finding_ids: set[str], register_ids: set[str],
              errors: list[str]) -> tuple[int, int, int]:
    manifest_path = run / "manifest.yaml"
    workflow_path = run / "workflow.yaml"
    adjudication_path = run / "adjudication.yaml"
    label = run.name
    for path in (manifest_path, workflow_path, adjudication_path):
        if not path.is_file():
            fail(errors, f"{label}: missing {path.name}")
            return 0, 0, 0

    manifest = yaml.safe_load(manifest_path.read_text()) or {}
    workflow = yaml.safe_load(workflow_path.read_text()) or {}
    adjudication = yaml.safe_load(adjudication_path.read_text()) or {}

    if manifest.get("schema") != "rgen.hazop-run/v1":
        fail(errors, f"{label}: wrong manifest schema")
    if not manifest.get("agents") or len(manifest["agents"]) < 3:
        fail(errors, f"{label}: fewer than three blind agents")
    if not manifest.get("inputs_sha256"):
        fail(errors, f"{label}: missing input hashes")

    nodes = set(manifest.get("nodes") or DEFAULT_NODES)
    guide_words = (set(manifest["guide_words"])
                   if manifest.get("guide_words") else None)
    run_findings = set(manifest.get("findings") or [])
    known_findings = finding_ids | run_findings

    rows = workflow.get("rows") or []
    if not rows:
        fail(errors, f"{label}: no rows")
    seen_nodes: set[str] = set()
    row_ids: set[str] = set()
    for index, row in enumerate(rows):
        rid = row.get("id", f"row[{index}]")
        missing = ROW_FIELDS - set(row)
        if missing:
            fail(errors, f"{label}/{rid}: missing fields {sorted(missing)}")
            continue
        row_ids.add(rid)
        seen_nodes.add(row["node"])
        if row["node"] not in nodes:
            fail(errors, f"{label}/{rid}: unknown node {row['node']}")
        if guide_words is not None and row["guide_word"] not in guide_words:
            fail(errors, f"{label}/{rid}: unknown guide word {row['guide_word']}")
        if row["safeguard_status"] not in SAFEGUARDS:
            fail(errors, f"{label}/{rid}: bad safeguard_status")
        if row["severity"] not in SEVERITY:
            fail(errors, f"{label}/{rid}: bad severity")
        if row["likelihood"] not in LIKELIHOOD:
            fail(errors, f"{label}/{rid}: bad likelihood")
        if row["disposition"] not in DISPOSITIONS:
            fail(errors, f"{label}/{rid}: bad disposition")
        evidence = str(row["evidence"]).split(":")[0]
        if not (ROOT / evidence).exists():
            fail(errors, f"{label}/{rid}: evidence path does not exist: {evidence}")
        finding = row.get("finding", "-")
        if finding != "-" and finding not in known_findings:
            fail(errors, f"{label}/{rid}: unknown finding {finding}")
        register = row.get("register", "-")
        if register != "-" and register not in register_ids:
            fail(errors, f"{label}/{rid}: unknown capability {register}")

    missing_nodes = nodes - seen_nodes
    if missing_nodes:
        fail(errors, f"{label}: no row for {sorted(missing_nodes)}")

    decisions = adjudication.get("decisions") or []
    decided_rows = {d.get("row") for d in decisions}
    for row in rows:
        if row.get("severity") in {"S1", "S2"}:
            authors = row.get("authors") or []
            if len(set(authors)) < 2 and row.get("id") not in decided_rows:
                fail(errors, f"{label}/{row.get('id')}: S1/S2 row needs two authors "
                             "or an adjudication entry")
    for decision in decisions:
        if decision.get("row") not in row_ids:
            fail(errors, f"{label}: adjudication references unknown row "
                         f"{decision.get('row')}")
    return len(rows), len(seen_nodes), len(decisions)


def main() -> int:
    errors: list[str] = []
    finding_ids = load_ids(FINDINGS, "findings", errors)
    for redteam in (REDTEAM, REDTEAM_CAPABILITIES):
        if redteam.is_file():
            finding_ids |= load_ids(redteam, "results", errors)
    register_ids = load_ids(CAPABILITIES, "capabilities", errors)
    runs = sorted(path for path in RUNS.iterdir() if path.is_dir())
    if not runs:
        fail(errors, "no HAZOP runs found")
    total_rows = total_nodes = total_decisions = 0
    for run in runs:
        rows, nodes, decisions = check_run(run, finding_ids, register_ids, errors)
        total_rows += rows
        total_nodes += nodes
        total_decisions += decisions
        print(f"  {run.name}: {rows} row(s), {nodes} node(s), {decisions} decision(s)")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"check_hazop_runs: {len(runs)} run(s), {total_rows} row(s), "
          f"{total_nodes} node(s), {total_decisions} adjudication decision(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
