#!/usr/bin/env python3
"""Verify an azoth bundle and, on a devnet, file it as an r-gen claim.

The bundle is produced by ``python -m azoth.rgen`` in the azoth checkout. This script is
the only writer: it re-hashes every document independently, checks the on-chain payloads
against the SDK's own structural rules, issues the validator's credential, and deploys the
claim, the validation, the K-Asset and the provenance anchors.

Two deployer keys, not two backends: the Claim contract refuses a validator equal to the
claimant, and the approval needs a third distinct key.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import actors  # noqa: E402
import assertions  # noqa: E402
import deploy as node  # noqa: E402
import fixtures  # noqa: E402
import preflight  # noqa: E402
import suite_base  # noqa: E402

QUALITY_KEYS = ("completeness", "correctness", "traceability", "fitness")
ANCHOR_KINDS = (
    "azoth:definition",
    "azoth:build",
    "azoth:statement",
    "azoth:cases",
    "azoth:agreement",
    "azoth:quality",
    "azoth:validation",
)
CLI = ROOT / "target" / "debug" / "rgen-cli"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.blake2b(_canonical(value), digest_size=32).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _integers_only(value: Any, path: str, problems: list[str]) -> None:
    if isinstance(value, (bool, int, str)):
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                problems.append(f"{path}: non-string key {key!r}")
            _integers_only(item, f"{path}.{key}", problems)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _integers_only(item, f"{path}[{index}]", problems)
        return
    problems.append(f"{path}: {type(value).__name__} has no r-gen wire form")


def verify(artifacts: Path) -> list[str]:
    """Re-hash every document and check the payloads against the bundle."""
    problems: list[str] = []
    manifest = _load(artifacts / "manifest.json")
    documents = manifest.get("documents", {})
    hashes: dict[str, str] = {}
    for name, record in documents.items():
        path = artifacts / str(record["path"])
        if not path.is_file():
            problems.append(f"{name}: {record['path']} is absent")
            continue
        actual = hashlib.blake2b(path.read_bytes(), digest_size=32).hexdigest()
        if actual != record["hash"]:
            problems.append(f"{name}: hashes {actual}, recorded {record['hash']}")
        hashes[str(name)] = actual

    claim = _load(artifacts / "payloads" / "claim.json")
    validation = _load(artifacts / "payloads" / "validation.json")
    anchors = _load(artifacts / "payloads" / "anchors.json")
    for label, payload in (("claim", claim), ("validation", validation), ("anchors", anchors)):
        _integers_only(payload, label, problems)
        recorded = manifest.get("payloads", {}).get(label)
        if _digest(payload) != recorded:
            problems.append(f"{label}: payload hashes {_digest(payload)}, recorded {recorded}")

    calc_id = str(manifest.get("calc_id"))
    if claim.get("statementHash") != hashes.get("statement"):
        problems.append("claim.statementHash does not name the statement document")
    if claim.get("definitionHash") != hashes.get("definition"):
        problems.append("claim.definitionHash does not name the definition document")
    if validation.get("characteristicsHash") != hashes.get("validation-evidence"):
        problems.append("validation.characteristicsHash does not name the evidence document")
    if claim.get("selectionCriteriaHash") != _digest(claim.get("selectionCriteria")):
        problems.append("claim.selectionCriteriaHash does not hash its criteria")
    if claim.get("work", {}).get("titleHash") != _digest(f"azoth:{calc_id}"):
        problems.append("claim.work.titleHash does not name the calculation")

    evidence = _load(artifacts / "documents" / "validation-evidence.json")
    if validation.get("commentHash") != _digest(evidence.get("comment")):
        problems.append("validation.commentHash does not hash the comment")

    cases_document = _load(artifacts / "documents" / "cases.json")
    replay = cases_document.get("replay", [])
    passed = sum(1 for report in replay if report.get("passed"))
    quantity = claim.get("quantity", {})
    if quantity.get("unit") != "validated-cases":
        problems.append(f"claim.quantity.unit is {quantity.get('unit')!r}")
    if quantity.get("value") != passed:
        problems.append(f"claim.quantity.value {quantity.get('value')} is not the {passed} passing case(s)")

    quality = validation.get("quality", {})
    if set(quality) != set(QUALITY_KEYS):
        problems.append(f"validation.quality keys are {sorted(quality)}")
    elif not all(isinstance(quality[key], int) and 1 <= quality[key] <= 5 for key in QUALITY_KEYS):
        problems.append("validation.quality values are not integers in 1..5")
    elif not 4 <= sum(quality.values()) <= 20:
        problems.append("validation.quality does not sum to 4..20")

    agreement = _load(artifacts / "documents" / "agreement.json")
    disagreements = list(agreement.get("mirrored", {}).get("disagreements", []))
    run_expected = agreement.get("run_expected") or {}
    disagreements += list(run_expected.get("disagreements", []))
    failures = len(replay) - passed
    statement = _load(artifacts / "documents" / "statement.json")
    warnings = len(statement.get("result", {}).get("warnings", []))
    matched = agreement.get("run_matched") is not None
    expected_verdict = (
        "invalid"
        if disagreements or failures
        else ("partial" if warnings or not matched else "valid")
    )
    if validation.get("verdict") != expected_verdict:
        problems.append(
            f"validation.verdict is {validation.get('verdict')!r}, the evidence implies {expected_verdict!r}"
        )

    if len(anchors) != len(ANCHOR_KINDS):
        problems.append(f"{len(anchors)} anchor(s), expected {len(ANCHOR_KINDS)}")
    seen: set[str] = {""}
    anchored: list[str] = []
    for anchor in anchors:
        if anchor.get("parentHash") not in seen:
            problems.append(f"anchor {anchor.get('kind')}: parent is not yet anchored")
        seen.add(str(anchor.get("hash")))
        anchored.append(str(anchor.get("hash")))
    if [anchor.get("kind") for anchor in anchors] != list(ANCHOR_KINDS):
        problems.append("the anchor kinds are not the expected order")
    if sorted(anchored) != sorted(hashes.values()):
        problems.append("the anchored hashes are not the document set")
    return problems


def _validate_with_sdk(kind: str, payload: dict[str, Any], at_height: int) -> None:
    """Run the SDK's own structural check through the CLI."""
    if not CLI.is_file():
        raise SystemExit(f"azoth_claim: {CLI} is absent; run `make client-build`")
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", prefix="rgen-azoth-", delete=False, encoding="utf-8"
    ) as handle:
        json.dump(payload, handle, sort_keys=True)
        path = Path(handle.name)
    try:
        result = subprocess.run(
            [str(CLI), "validate-payload", kind, str(path), "--at-height", str(at_height)],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        path.unlink(missing_ok=True)
    if result.returncode != 0:
        raise SystemExit(f"azoth_claim: {kind} payload refused: {result.stderr.strip()}")


def _substitute(
    claim: dict[str, Any],
    validation: dict[str, Any],
    *,
    height: int,
    deadline_blocks: int,
    comment_blocks: int | None,
    validator_credential: str,
) -> None:
    claim["deadlineHeight"] = height + deadline_blocks
    if comment_blocks is not None:
        claim["commentUntilHeight"] = height + comment_blocks
        if claim["commentUntilHeight"] > claim["deadlineHeight"]:
            raise SystemExit("azoth_claim: the comment window exceeds the deadline")
    validation["credentialUri"] = validator_credential


def deploy(
    artifacts: Path,
    *,
    claimant: str = "alice",
    validator: str = "bob",
    approver: str = "carol",
    deadline_blocks: int = 100_000,
    comment_blocks: int | None = None,
    approve: bool = False,
) -> dict[str, Any]:
    problems = verify(artifacts)
    if problems:
        raise SystemExit("azoth_claim: " + "\n  ".join(["bundle is not intact:"] + problems))
    if claimant == validator:
        raise SystemExit("azoth_claim: the claimant and validator must be distinct keys")
    if approve and approver in (claimant, validator):
        raise SystemExit("azoth_claim: the approver must be distinct from both")

    if not preflight.require_devnet("azoth_claim"):
        return {"status": "not_run"}

    names = [claimant, validator] + ([approver] if approve else [])
    addresses = suite_base.setup(names)

    claim = _load(artifacts / "payloads" / "claim.json")
    validation = _load(artifacts / "payloads" / "validation.json")
    anchors = _load(artifacts / "payloads" / "anchors.json")
    criteria = claim["selectionCriteria"]

    credential = suite_base.issue(
        addresses,
        validator,
        "Validator",
        "validator",
        discipline=criteria["discipline"],
        jurisdiction=criteria["jurisdiction"],
        level=criteria["minLevel"],
    )
    height = actors.block_height()
    _substitute(
        claim,
        validation,
        height=height,
        deadline_blocks=deadline_blocks,
        comment_blocks=comment_blocks,
        validator_credential=credential,
    )
    _validate_with_sdk("claim", claim, height)
    _validate_with_sdk("validation", validation, 0)

    created = fixtures.claim(claimant, claim)
    assertions.expect_ok("azoth claim", created)
    claim_uri = created[1]["uri"]

    validated = fixtures.claim_validate(claim_uri, credential, validator, validation)
    assertions.expect_ok("azoth validation", validated)
    kasset_uri = validated[1]["uri"]

    if approve:
        approver_credential = suite_base.issue(
            addresses,
            approver,
            "Approver",
            "approver",
            discipline=criteria["discipline"],
            jurisdiction=criteria["jurisdiction"],
            level=criteria["minLevel"],
        )
        approval = suite_base.approval(approver_credential, addresses[approver])
        reply = fixtures.kasset_approve(kasset_uri, approver_credential, approver, approval)
        assertions.expect_ok("azoth K-Asset approval", reply)

    provenance = fixtures.provenance_create(kasset_uri, [validator], key=claimant)
    assertions.expect_ok("azoth provenance", provenance)
    provenance_uri = provenance[1]["uri"]

    for anchor in anchors:
        reply = fixtures.provenance_anchor(provenance_uri, claimant, anchor)
        assertions.expect_ok(f"anchor {anchor['kind']}", reply)

    state = fixtures.read(provenance_uri, "get")
    assertions.expect_ok("provenance read", state)
    recorded = state[1]["anchors"]
    if [entry["hash"] for entry in recorded] != [anchor["hash"] for anchor in anchors]:
        raise SystemExit("azoth_claim: the anchored hashes are not the bundle's order")
    for anchor in anchors:
        found = fixtures.read(provenance_uri, "verify", [anchor["hash"]])
        assertions.expect_ok(f"verify {anchor['kind']}", found)
        if found[1] is not True:
            raise SystemExit(f"azoth_claim: {anchor['kind']} is not present")

    claim_state = fixtures.read(claim_uri, "get")
    assertions.expect_ok("claim read", claim_state)
    kasset_state = fixtures.read(kasset_uri, "get")
    assertions.expect_ok("K-Asset read", kasset_state)

    record = {
        "networkId": _network_id(),
        "calcId": _load(artifacts / "manifest.json")["calc_id"],
        "claim": claim_uri,
        "kasset": kasset_uri,
        "provenance": provenance_uri,
        "claimant": addresses[claimant],
        "validator": addresses[validator],
        "credential": credential,
        "approved": approve,
        "claimStatus": claim_state[1].get("status"),
        "kassetStatus": kasset_state[1].get("status"),
        "quantity": kasset_state[1].get("quantity"),
        "quality": kasset_state[1].get("quality"),
        "verdict": kasset_state[1].get("verdict"),
        "anchors": [anchor["hash"] for anchor in anchors],
    }
    out = ROOT / "deployments" / "azoth.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + "\n")
    print(f"azoth_claim: wrote {out.relative_to(ROOT)}")
    return record


def _network_id() -> str | None:
    try:
        status = node.http_json("GET", f"{node.NODE}/api/v1/status")
    except Exception:
        return None
    return status.get("networkId")


def verify_deployment() -> int:
    path = ROOT / "deployments" / "azoth.json"
    if not path.is_file():
        print(f"azoth_claim: {path.relative_to(ROOT)} is absent", file=sys.stderr)
        return 1
    record = _load(path)
    problems: list[str] = []
    state = fixtures.read(record["claim"], "get")
    if not (isinstance(state, tuple) and state and state[0] is True):
        problems.append("the claim could not be read")
    else:
        if state[1].get("status") != "validated":
            problems.append(f"claim status is {state[1].get('status')!r}")
        if state[1].get("validationRef") is None:
            problems.append("the claim has no validation reference")
    kasset = fixtures.read(record["kasset"], "get")
    if not (isinstance(kasset, tuple) and kasset and kasset[0] is True):
        problems.append("the K-Asset could not be read")
    else:
        for key in ("quantity", "quality", "verdict"):
            if kasset[1].get(key) != record.get(key):
                problems.append(f"K-Asset {key} differs from the deployment record")
        if record.get("approved") and kasset[1].get("status") != "approved":
            problems.append(f"K-Asset status is {kasset[1].get('status')!r}")
    provenance = fixtures.read(record["provenance"], "get")
    if not (isinstance(provenance, tuple) and provenance and provenance[0] is True):
        problems.append("the provenance cell could not be read")
    else:
        if [anchor["hash"] for anchor in provenance[1]["anchors"]] != record["anchors"]:
            problems.append("the anchors differ from the deployment record")
    for digest in record["anchors"]:
        found = fixtures.read(record["provenance"], "verify", [digest])
        if not (isinstance(found, tuple) and len(found) == 2 and found[1] is True):
            problems.append(f"{digest}: not found")
    if problems:
        for problem in problems:
            print(f"azoth_claim: {problem}", file=sys.stderr)
        return 1
    print("azoth_claim: deployment verified")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="azoth_claim")
    sub = parser.add_subparsers(dest="command", required=True)

    checked = sub.add_parser("verify", help="re-hash a bundle without a node")
    checked.add_argument("--artifacts", type=Path, required=True)

    for name in ("deploy", "demo"):
        emitted = sub.add_parser(name, help="file the bundle on the devnet")
        emitted.add_argument("--artifacts", type=Path, required=True)
        emitted.add_argument("--claimant", default="alice")
        emitted.add_argument("--validator", default="bob")
        emitted.add_argument("--approver", default="carol")
        emitted.add_argument("--deadline-blocks", type=int, default=100_000)
        emitted.add_argument("--comment-blocks", type=int, default=None)
        emitted.add_argument("--approve", action="store_true", default=(name == "demo"))
        emitted.add_argument("--json", action="store_true")

    sub.add_parser("verify-deployment", help="re-read a filed deployment")

    args = parser.parse_args(argv)
    if args.command == "verify":
        problems = verify(args.artifacts)
        if problems:
            for problem in problems:
                print(f"azoth_claim: {problem}", file=sys.stderr)
            return 1
        print("azoth_claim: bundle verified")
        return 0
    if args.command == "verify-deployment":
        return verify_deployment()
    record = deploy(
        args.artifacts,
        claimant=args.claimant,
        validator=args.validator,
        approver=args.approver,
        deadline_blocks=args.deadline_blocks,
        comment_blocks=args.comment_blocks,
        approve=args.approve,
    )
    if record.get("status") == "not_run":
        return 2
    if args.json:
        print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
