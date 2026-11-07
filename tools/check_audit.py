#!/usr/bin/env python3
"""Check the audit, HAZOP, rigor, and improvement manifests.

The audit record is only useful if it cannot silently drift from the code, the proof
manifest, and the docs. This gate checks the four YAML manifests under ``spec/`` against
each other and against the deployed arms, the Pareto theorem list, the Lean declarations,
and the mdBook summary.

Modes:

* ``--schema-only`` checks structure and cross-references without the docs/theorem sweep.
* ``--strict`` (default in CI) performs every check.
* ``--phase2`` additionally requires an approved review and no open P0/P1 finding.
* ``--phase1`` rejects a diff under ``contracts/`` or ``spec/lean/`` from the baseline.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FINDINGS = ROOT / "spec" / "audit" / "findings.yaml"
WORKSHEET = ROOT / "spec" / "hazop" / "worksheet.yaml"
RIGOR = ROOT / "spec" / "proofs" / "rigor.yaml"
IMPROVEMENTS = ROOT / "spec" / "improvements" / "rholang.yaml"
CORE = ROOT / "spec" / "flows" / "core.yaml"
PARETO = ROOT / "spec" / "pareto.yaml"
LEAN = ROOT / "spec" / "lean" / "RGen"
DOCS = ROOT / "docs" / "src"
SUMMARY = DOCS / "SUMMARY.md"

GUIDE_WORDS = [
    "No/Not", "More", "Less", "As well as", "Part of", "Reverse", "Other than",
    "Late", "Early", "Before", "After", "Duplicate/Replay", "Stale",
    "Substitute/confused-deputy", "Partial commit",
]
NODES = {
    "root-install", "identity", "issuer-credential-proof", "claim-validation",
    "kasset-nesting", "value-proposition", "oracle", "provenance",
    "registries-factories", "deployment-phlo",
}
SEVERITY = {"S1": 4, "S2": 3, "S3": 2, "S4": 1}
LIKELIHOOD = {"A": 4, "B": 3, "C": 2, "D": 1}
VERDICTS = {"proved", "proved-but-narrower", "unproved", "overclaim", "false"}
DISPOSITIONS = {"open", "accepted", "fixed", "accept-risk", "rejected"}
ROW_DISPOSITIONS = {"open", "fixed", "accept-risk", "rejected", "no-finding"}
SAFEGUARDS = {"holds", "partial", "none"}
PRIORITIES = {"P0", "P1", "P2"}
DIRECTIONS = {
    "model-permissive", "model-stricter", "effect-omitting", "shape-different", "mixed",
}
AUDIT_PAGES = [
    "reference/audit-charter.md",
    "reference/object-capabilities.md",
    "reference/hazop.md",
    "reference/proof-audit.md",
    "reference/rigor-roadmap.md",
    "reference/rholang-improvements.md",
]
DECL = re.compile(r"\b(?:theorem|lemma|def)\s+([A-Za-z0-9_']+)")
RGA = re.compile(r"^RGA-\d{3}$")
HZ = re.compile(r"^HZ-[A-Z]+-\d{3}$")
PRF = re.compile(r"^PRF-\d{3}$")
DIV = re.compile(r"^DIV-\d{3}$")
ASM = re.compile(r"^ASM-\d{3}$")
INV = re.compile(r"^INV-[A-Z0-9]+$")
LR = re.compile(r"^LR-\d{2}$")
RR = re.compile(r"^RR-\d{2}$")
RLEAN = re.compile(r"`(RGen\.[A-Za-z0-9_.']+)`")


def load(path: Path, errors: list[str]) -> dict:
    try:
        data = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f"{path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append(f"{path.relative_to(ROOT)}: top level is not a mapping")
        return {}
    return data


def lean_decls() -> set[str]:
    names: set[str] = set()
    for path in sorted(LEAN.rglob("*.lean")):
        if ".lake" in path.parts:
            continue
        names.update(DECL.findall(path.read_text()))
    return names


def core_arms() -> set[tuple[str, str, str]]:
    arms: set[tuple[str, str, str]] = set()
    entry: dict[str, str] = {}
    for raw in CORE.read_text().splitlines():
        line = raw.strip()
        if line.startswith("- file: "):
            if entry.get("file"):
                arms.add((entry["file"], entry.get("contract", ""), entry.get("arm", "")))
            entry = {"file": line[len("- file: "):]}
        elif line.startswith("contract: "):
            entry["contract"] = line[len("contract: "):]
        elif line.startswith("arm: "):
            entry["arm"] = line[len("arm: "):]
    if entry.get("file"):
        arms.add((entry["file"], entry.get("contract", ""), entry.get("arm", "")))
    return arms


def pareto_theorems() -> set[str]:
    names: set[str] = set()
    in_theorems = False
    for raw in PARETO.read_text().splitlines():
        line = raw.rstrip()
        if line.startswith("theorems:"):
            in_theorems = True
            continue
        if in_theorems and line and not line.startswith(" "):
            break
        if in_theorems and line.strip().startswith("- "):
            names.add(line.strip()[2:].strip())
    return names


def check_common(manifest: dict, name: str, errors: list[str]) -> None:
    if not manifest:
        errors.append(f"{name}: empty or unreadable")
        return
    if not manifest.get("schema_version"):
        errors.append(f"{name}: missing schema_version")
    if not manifest.get("baseline"):
        errors.append(f"{name}: missing baseline")


def check_findings(data: dict, errors: list[str]) -> tuple[dict, dict]:
    check_common(data, "findings", errors)
    review = data.get("review") or {}
    for field in ("status", "date", "reviewers", "independent_sample"):
        if field not in review:
            errors.append(f"findings.review: missing {field}")
    findings = data.get("findings") or []
    if not findings:
        errors.append("findings: no findings")
    by_id: dict[str, dict] = {}
    for f in findings:
        fid = f.get("id", "")
        if not RGA.match(fid):
            errors.append(f"findings: bad id {fid!r}")
        if fid in by_id:
            errors.append(f"findings: duplicate id {fid}")
        by_id[fid] = f
        for field in ("title", "severity", "likelihood", "risk", "priority", "category",
                      "evidence", "claim", "verdict", "arms", "actions", "disposition", "note"):
            if field not in f:
                errors.append(f"{fid}: missing {field}")
        if f.get("severity") not in SEVERITY:
            errors.append(f"{fid}: bad severity {f.get('severity')!r}")
        if f.get("likelihood") not in LIKELIHOOD:
            errors.append(f"{fid}: bad likelihood {f.get('likelihood')!r}")
        expected = SEVERITY.get(f.get("severity"), 0) * LIKELIHOOD.get(f.get("likelihood"), 0)
        if f.get("risk") != expected:
            errors.append(f"{fid}: risk {f.get('risk')} != {expected}")
        if f.get("priority") not in PRIORITIES:
            errors.append(f"{fid}: bad priority {f.get('priority')!r}")
        if f.get("verdict") not in VERDICTS:
            errors.append(f"{fid}: bad verdict {f.get('verdict')!r}")
        if f.get("disposition") not in DISPOSITIONS:
            errors.append(f"{fid}: bad disposition {f.get('disposition')!r}")
        if not f.get("evidence"):
            errors.append(f"{fid}: no evidence")
        for action in f.get("actions") or []:
            if action != "accept-risk" and not (LR.match(action) or RR.match(action)):
                errors.append(f"{fid}: bad action {action!r}")
        if f.get("severity") == "S1" and f.get("disposition") == "open" and not f.get("actions"):
            errors.append(f"{fid}: open S1 has no action")
    return by_id, review


def check_arms(data: dict, errors: list[str], node_ids: set[str],
               decls: set[str]) -> dict:
    entries = data.get("arms") or []
    deployed = core_arms()
    seen: set[tuple[str, str, str]] = set()
    for entry in entries:
        for field in ("file", "contract", "arm", "node", "disposition", "flow_status", "lean",
                      "guard_eq", "divergences", "guard_fidelity", "guard_fidelity_finding"):
            if field not in entry or entry.get(field) == "":
                errors.append(f"arms: missing {field}: {entry}")
        key = (entry.get("file", ""), entry.get("contract", ""), entry.get("arm", ""))
        if key in seen:
            errors.append(f"arms: duplicate {key}")
        seen.add(key)
        if key not in deployed:
            errors.append(f"arms: not a deployed arm: {key}")
        if entry.get("node") not in node_ids:
            errors.append(f"arms: bad node {entry.get('node')!r} for {key}")
        if entry.get("disposition") not in {"model-reviewed", "infrastructure-reviewed",
                                            "fixed", "accept-risk"}:
            errors.append(f"arms: bad disposition {entry.get('disposition')!r} for {key}")
        if entry.get("flow_status") not in {"proved-model", "proved-conformance", "owed", "open"}:
            errors.append(f"arms: bad flow_status {entry.get('flow_status')!r} for {key}")
        if entry.get("guard_fidelity") not in {"guarded", "divergence", "unverified",
                                               "not-applicable"}:
            errors.append(f"arms: bad guard_fidelity {entry.get('guard_fidelity')!r} for {key}")
        for div in entry.get("divergences") or []:
            if not DIV.match(div):
                errors.append(f"arms: bad divergence id {div!r} for {key}")
        if entry.get("flow_status") in {"proved-model", "proved-conformance"} and \
                entry.get("guard_fidelity") == "not-applicable" and \
                not entry.get("guard_fidelity_reason"):
            errors.append(f"arms: {key} is proved-model, not-applicable, and has no reason")
        guard_eq = entry.get("guard_eq", "-")
        if entry.get("guard_fidelity") == "guarded":
            if guard_eq == "-":
                errors.append(f"arms: {key} is guarded without a guard_eq declaration")
            elif guard_eq.rsplit(".", 1)[-1] not in decls:
                errors.append(f"arms: {key} guard_eq {guard_eq} not found")
        lean = entry.get("lean", "-")
        if entry.get("flow_status") in {"proved-model", "proved-conformance"}:
            if lean == "-":
                errors.append(f"arms: {key} is {entry.get('flow_status')} without a Lean declaration")
            elif lean.rsplit(".", 1)[-1] not in decls:
                errors.append(f"arms: {key} Lean declaration {lean} not found")
    for key in sorted(deployed - seen):
        errors.append(f"arms: deployed arm missing from audit: {key}")
    for key in sorted(seen - deployed):
        errors.append(f"arms: audit arm is not deployed: {key}")
    return {f"{e.get('file')}|{e.get('contract')}|{e.get('arm')}": e for e in entries}


def check_hazop(data: dict, errors: list[str], finding_ids: set[str],
                lr_ids: set[str], rr_ids: set[str]) -> set[str]:
    check_common(data, "hazop", errors)
    if data.get("guide_words") != GUIDE_WORDS:
        errors.append("hazop: guide_words do not match the 15-word vocabulary")
    nodes = data.get("nodes") or []
    node_ids = {n.get("id") for n in nodes}
    if node_ids != NODES:
        errors.append(f"hazop: node set {sorted(node_ids)} != expected {sorted(NODES)}")
    for node in nodes:
        for field in ("id", "title", "intent", "invariants", "parameters", "na"):
            if field not in node:
                errors.append(f"hazop node {node.get('id')}: missing {field}")
    rows = data.get("rows") or []
    if not 110 <= len(rows) <= 180:
        errors.append(f"hazop: {len(rows)} rows outside the 110..180 target")
    row_by_id: dict[str, dict] = {}
    for row in rows:
        rid = row.get("id", "")
        if not HZ.match(rid):
            errors.append(f"hazop: bad row id {rid!r}")
        if rid in row_by_id:
            errors.append(f"hazop: duplicate row {rid}")
        row_by_id[rid] = row
        for field in ("node", "guide_word", "parameter", "deviation", "cause", "consequence",
                      "safeguard", "safeguard_status", "severity", "likelihood", "risk",
                      "action", "finding", "negative", "disposition"):
            if field not in row:
                errors.append(f"{rid}: missing {field}")
        if row.get("node") not in node_ids:
            errors.append(f"{rid}: bad node {row.get('node')!r}")
        if row.get("guide_word") not in GUIDE_WORDS:
            errors.append(f"{rid}: bad guide word {row.get('guide_word')!r}")
        node = next((n for n in nodes if n.get("id") == row.get("node")), None)
        if node and row.get("parameter") not in node.get("parameters", []):
            errors.append(f"{rid}: parameter {row.get('parameter')!r} not on node")
        if row.get("safeguard_status") not in SAFEGUARDS:
            errors.append(f"{rid}: bad safeguard status {row.get('safeguard_status')!r}")
        if row.get("severity") not in SEVERITY:
            errors.append(f"{rid}: bad severity")
        if row.get("likelihood") not in LIKELIHOOD:
            errors.append(f"{rid}: bad likelihood")
        expected = SEVERITY.get(row.get("severity"), 0) * LIKELIHOOD.get(row.get("likelihood"), 0)
        if row.get("risk") != expected:
            errors.append(f"{rid}: risk {row.get('risk')} != {expected}")
        action = row.get("action", "")
        if action not in {"none", "accept-risk"} and not (LR.match(action) or RR.match(action)):
            errors.append(f"{rid}: bad action {action!r}")
        if action.startswith("LR-") and action not in lr_ids:
            errors.append(f"{rid}: unknown roadmap item {action}")
        if action.startswith("RR-") and action not in rr_ids:
            errors.append(f"{rid}: unknown improvement {action}")
        finding = row.get("finding", "-")
        if finding != "-" and finding not in finding_ids:
            errors.append(f"{rid}: unknown finding {finding}")
        if row.get("safeguard_status") in {"partial", "none"} and action == "none":
            errors.append(f"{rid}: partial/no safeguard without LR/RR/accept-risk action")
        if row.get("negative"):
            if row.get("safeguard_status") != "holds":
                errors.append(f"{rid}: negative row without a holding safeguard")
            if row.get("disposition") != "no-finding":
                errors.append(f"{rid}: negative row disposition is not no-finding")
        elif row.get("disposition") == "no-finding":
            errors.append(f"{rid}: positive row marked no-finding")
        if row.get("disposition") not in ROW_DISPOSITIONS:
            errors.append(f"{rid}: bad disposition {row.get('disposition')!r}")
    coverage = data.get("coverage") or []
    expected_cells = {(n, g) for n in NODES for g in GUIDE_WORDS}
    seen_cells: set[tuple[str, str]] = set()
    for cell in coverage:
        key = (cell.get("node"), cell.get("guide_word"))
        if key in seen_cells:
            errors.append(f"hazop coverage duplicate {key}")
        seen_cells.add(key)
        if key not in expected_cells:
            errors.append(f"hazop coverage unknown cell {key}")
        if cell.get("status") == "na":
            if not cell.get("reason"):
                errors.append(f"hazop coverage {key}: na without a reason")
        elif cell.get("status") == "covered":
            refs = cell.get("refs") or []
            if not refs:
                errors.append(f"hazop coverage {key}: covered without refs")
            for ref in refs:
                row = row_by_id.get(ref)
                if row is None:
                    errors.append(f"hazop coverage {key}: unknown row {ref}")
                elif (row.get("node"), row.get("guide_word")) != key:
                    errors.append(f"hazop coverage {key}: row {ref} is {row.get('node')}/{row.get('guide_word')}")
        else:
            errors.append(f"hazop coverage {key}: bad status {cell.get('status')!r}")
    for key in sorted(expected_cells - seen_cells):
        errors.append(f"hazop coverage missing {key}")
    referenced = {ref for cell in coverage for ref in (cell.get("refs") or [])}
    for rid in row_by_id:
        if rid not in referenced:
            errors.append(f"hazop row {rid} is not referenced by coverage")
    if len(rows) and sum(1 for r in rows if r.get("negative")) < 12:
        errors.append("hazop: fewer than 12 negative rows")
    return node_ids


def check_rigor(data: dict, errors: list[str], decls: set[str],
                finding_ids: set[str]) -> set[str]:
    check_common(data, "rigor", errors)
    claims = data.get("claims") or []
    by_theorem = {c.get("theorem"): c for c in claims}
    missing = pareto_theorems() - set(by_theorem)
    for theorem in sorted(missing):
        errors.append(f"rigor: Pareto theorem {theorem} has no claim entry")
    for claim in claims:
        cid = claim.get("id", "")
        if not PRF.match(cid):
            errors.append(f"rigor: bad claim id {cid!r}")
        theorem = claim.get("theorem", "")
        short = theorem.rsplit(".", 1)[-1]
        if short not in decls:
            errors.append(f"{cid}: theorem {theorem} not found")
        if claim.get("verdict") not in VERDICTS:
            errors.append(f"{cid}: bad verdict {claim.get('verdict')!r}")
        finding = claim.get("finding", "-")
        if finding != "-" and finding not in finding_ids:
            errors.append(f"{cid}: unknown finding {finding}")
    for kind, pattern in (("divergence", DIV), ("assumption", ASM)):
        for item in data.get(kind + "s") or []:
            iid = item.get("id", "")
            if not pattern.match(iid):
                errors.append(f"rigor: bad {kind} id {iid!r}")
            finding = item.get("finding", "-")
            if finding != "-" and finding not in finding_ids:
                errors.append(f"{iid}: unknown finding {finding}")
    for div in data.get("divergences") or []:
        if div.get("direction") not in DIRECTIONS:
            errors.append(f"{div.get('id')}: bad direction {div.get('direction')!r}")
    for cov in data.get("coverage") or []:
        if not INV.match(cov.get("id", "")):
            errors.append(f"rigor: bad coverage id {cov.get('id')!r}")
        theorem = cov.get("theorem", "")
        if theorem.rsplit(".", 1)[-1] not in decls:
            errors.append(f"{cov.get('id')}: theorem {theorem} not found")
    roadmap = data.get("roadmap") or []
    lr_ids = {item.get("id") for item in roadmap}
    for item in roadmap:
        if not LR.match(item.get("id", "")):
            errors.append(f"rigor: bad roadmap id {item.get('id')!r}")
        if item.get("priority") not in PRIORITIES:
            errors.append(f"{item.get('id')}: bad priority")
        for finding in item.get("findings") or []:
            if finding not in finding_ids:
                errors.append(f"{item.get('id')}: unknown finding {finding}")
    return {x for x in lr_ids if x}


def check_improvements(data: dict, errors: list[str], finding_ids: set[str],
                       row_ids: set[str]) -> set[str]:
    check_common(data, "improvements", errors)
    items = data.get("items") or []
    if not items:
        errors.append("improvements: no items")
    rr_ids: set[str] = set()
    for item in items:
        iid = item.get("id", "")
        if not RR.match(iid):
            errors.append(f"improvements: bad id {iid!r}")
        if iid in rr_ids:
            errors.append(f"improvements: duplicate {iid}")
        rr_ids.add(iid)
        if item.get("priority") not in PRIORITIES:
            errors.append(f"{iid}: bad priority {item.get('priority')!r}")
        if item.get("finding") not in finding_ids:
            errors.append(f"{iid}: unknown finding {item.get('finding')}")
        for ref in item.get("hazop") or []:
            if ref not in row_ids:
                errors.append(f"{iid}: unknown HAZOP row {ref}")
        files = item.get("files") or []
        if not files:
            errors.append(f"{iid}: no files")
        for entry in files:
            path = entry.get("path", "")
            if not (ROOT / path).is_file():
                errors.append(f"{iid}: missing file {path}")
            for field in ("function", "lines"):
                if not entry.get(field):
                    errors.append(f"{iid}: {path} missing {field}")
        for field in ("compatibility", "tests", "status", "action", "title"):
            if not item.get(field):
                errors.append(f"{iid}: missing {field}")
        if item.get("status") not in {"proposed", "accepted", "partial", "fixed", "rejected", "accept-risk"}:
            errors.append(f"{iid}: bad status {item.get('status')!r}")
    return rr_ids


def check_docs(errors: list[str], decls: set[str]) -> None:
    summary = SUMMARY.read_text() if SUMMARY.is_file() else ""
    for page in AUDIT_PAGES:
        path = DOCS / page
        if not path.is_file():
            errors.append(f"docs: missing {page}")
        if page not in summary:
            errors.append(f"docs: {page} not in SUMMARY.md")
    for path in sorted(DOCS.rglob("*.md")):
        text = path.read_text()
        for ref in RLEAN.findall(text):
            short = ref.rsplit(".", 1)[-1]
            if short in decls:
                continue
            # Allow a module reference such as RGen.Arms.Credential.
            module = ROOT / "spec" / "lean" / (ref.replace(".", "/") + ".lean")
            if module.is_file():
                continue
            errors.append(f"docs: {path.relative_to(ROOT)} cites missing {ref}")


def check_phase2(data: dict, review: dict, errors: list[str]) -> None:
    if review.get("status") != "approved":
        errors.append("phase2: review.status is not approved")
    if not review.get("reviewers"):
        errors.append("phase2: no reviewers recorded")
    for f in data.get("findings") or []:
        if f.get("priority") in {"P0", "P1"} and f.get("disposition") == "open":
            errors.append(f"phase2: {f.get('id')} is open at {f.get('priority')} "
                          "(review must accept, reject, fix, or accept-risk it)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema-only", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--phase2", action="store_true")
    parser.add_argument("--phase1", action="store_true")
    args = parser.parse_args()
    strict = args.strict or not args.schema_only

    errors: list[str] = []
    findings = load(FINDINGS, errors)
    worksheet = load(WORKSHEET, errors)
    rigor = load(RIGOR, errors)
    improvements = load(IMPROVEMENTS, errors)

    decls = lean_decls()
    finding_ids, review = check_findings(findings, errors)
    node_ids = {n.get("id") for n in worksheet.get("nodes") or []}
    check_arms(findings, errors, node_ids, decls)
    lr_ids = check_rigor(rigor, errors, decls, set(finding_ids))
    row_ids = {r.get("id") for r in worksheet.get("rows") or []}
    rr_ids = check_improvements(improvements, errors, set(finding_ids), row_ids)
    check_hazop(worksheet, errors, set(finding_ids), lr_ids, rr_ids)
    if strict:
        check_docs(errors, decls)
    if args.phase2:
        check_phase2(findings, review, errors)
    if args.phase1:
        baseline = findings.get("baseline", "")
        try:
            diff = subprocess.check_output(
                ["git", "diff", "--name-only", baseline, "--", "contracts", "spec/lean"],
                cwd=ROOT, text=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            errors.append(f"phase1: cannot compare to baseline: {exc}")
        else:
            if diff.strip():
                errors.append("phase1: contracts/ or spec/lean/ changed:\n" + diff)

    if errors:
        for error in errors:
            print(f"check_audit: {error}", file=sys.stderr)
        print(f"check_audit: {len(errors)} error(s)", file=sys.stderr)
        return 1

    print(f"check_audit: {len(findings.get('findings') or [])} finding(s), "
          f"{len(worksheet.get('nodes') or [])} node(s), "
          f"{len(worksheet.get('coverage') or [])} coverage cell(s), "
          f"{len(worksheet.get('rows') or [])} HAZOP row(s), "
          f"{len(rigor.get('claims') or [])} claim(s), "
          f"{len(improvements.get('items') or [])} improvement(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
