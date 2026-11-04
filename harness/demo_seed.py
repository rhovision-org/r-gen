#!/usr/bin/env python3
"""Seed a real bridge-inspection scenario on the running devnet.

Every value in the catalogue is a registry URI returned by a real deploy. The off-chain
documents under ``harness/demo/artifacts`` are hashed; only the hashes reach the chain.

The seed also writes encrypted browser keystores under ``.demo/keystores`` so the demo can
move between the issuer, claimant, validator, approver and adjudicator wallets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def requested_net() -> str:
    for index, value in enumerate(sys.argv):
        if value == "--net" and index + 1 < len(sys.argv):
            return sys.argv[index + 1]
        if value.startswith("--net="):
            return value.split("=", 1)[1]
    return "devnet"


NET = requested_net()
if NET == "testnet":
    profile = json.loads((ROOT / "configs" / "testnet.json").read_text())
    os.environ.setdefault("RGEN_NET", "testnet")
    os.environ.setdefault("RGEN_REMOTE", "1")
    os.environ.setdefault("RGEN_NODE", profile["node"])
    os.environ.setdefault("RGEN_KEYS", ".testnet/keys.json")
    os.environ.setdefault("RGEN_SHARD", profile["shardId"])
    os.environ.setdefault("RGEN_MANIFEST", "deployments/testnet.json")
    os.environ.setdefault("RGEN_FAUCET_URL", profile["faucetUrl"])
    os.environ.setdefault("RGEN_PHLO_LIMIT", str(profile.get("phloLimit", 8_000_000)))

sys.path.insert(0, str(ROOT / "harness"))

import actors  # noqa: E402
import assertions  # noqa: E402
import deploy as node  # noqa: E402
import fixtures  # noqa: E402
import preflight  # noqa: E402

ARTIFACTS = ROOT / "harness" / "demo" / "artifacts" / "bridge-deck-2026"
CRITERIA = {
    "ctype": "Validator",
    "discipline": "structural",
    "jurisdiction": "US-TX",
    "role": "validator",
    "minLevel": 1,
}
ORACLE_REQUIREMENT = {
    "ctype": "Oracle",
    "discipline": "structural",
    "jurisdiction": "US-TX",
    "role": "oracle",
    "minLevel": 1,
}


def digest(name: str) -> str:
    return hashlib.blake2b((ARTIFACTS / name).read_bytes(), digest_size=32).hexdigest()


def hash_text(value: str) -> str:
    return hashlib.blake2b(value.encode("utf-8"), digest_size=32).hexdigest()


def build_keystore(name: str, label: str, keys: Path, out_dir: Path, password: str) -> Path:
    binary = ROOT / "target" / "debug" / "rgen-cli"
    if not binary.is_file():
        subprocess.run(["cargo", "build", "-p", "rgen-cli"], cwd=ROOT, check=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{label}.json"
    subprocess.run(
        [
            str(binary),
            "--keys",
            str(keys),
            "keystore",
            "encrypt",
            "--name",
            name,
            "--password",
            password,
            "--out",
            str(out),
        ],
        cwd=ROOT,
        check=True,
    )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--net", choices=["devnet", "testnet"], default="devnet")
    parser.add_argument("--catalogue", type=Path, default=ROOT / "deployments" / "catalogue.json")
    parser.add_argument("--keystores", type=Path, default=None)
    parser.add_argument(
        "--password",
        default="rgen-demo-password",
        help="password for the generated demo keystores",
    )
    args = parser.parse_args()

    if args.keystores is None:
        args.keystores = ROOT / ".demo" / f"keystores-{args.net}"
    if args.net == "devnet":
        if not preflight.require_devnet("demo_seed"):
            return 2
    else:
        report = ROOT / ".testnet" / "preflight.json"
        if not report.is_file():
            print("demo_seed: run `make testnet-preflight` first", file=sys.stderr)
            return 2
        if not node.keys_path().is_file():
            print("demo_seed: run `make testnet-keys` first", file=sys.stderr)
            return 2

    for name in ("alice", "bob", "carol", "dave"):
        actors.ensure_vault(name)

    alice = actors.address("alice")
    bob = actors.address("bob")
    carol = actors.address("carol")
    dave = actors.address("dave")
    height = actors.block_height()
    suffix = hash_text(str(height))[:8]

    identities = {}
    for name in ("alice", "bob", "carol", "dave"):
        reply = fixtures.ensure_identity(name, f"{name}-{suffix}")
        assertions.expect_ok(f"{name} identity", reply)
        lookup = fixtures.read(
            fixtures.comp("identity-directory"), "lookup", [actors.address(name)]
        )
        assertions.expect_ok(f"{name} directory lookup", lookup)
        identities[name] = lookup[1]

    bob_cred = fixtures.issue(bob, "Validator", "structural", "US-TX", "validator", 1)[1]
    carol_cred = fixtures.issue(carol, "Approver", "structural", "US-TX", "approver", 1)[1]
    dave_cred = fixtures.issue(dave, "Oracle", "structural", "US-TX", "oracle", 1)[1]

    vp_req = {
        "subjectRef": {"type": "project", "id": "cedar-crossing-deck-2026", "uri": ""},
        "statementHash": digest("value-proposition.md"),
        "valueModelHash": hash_text("one K-Asset per validated twelve-bay inspection"),
        "beneficiaries": [alice],
        "termsHash": digest("terms.md"),
        "selectionCriteria": CRITERIA,
        "deadlineHeight": height + 100_000,
    }
    vp = fixtures.vp_propose("alice", vp_req)
    assertions.expect_ok("value proposition", vp)
    vp_uri = vp[1]["uri"]
    reply = fixtures.vp_validate(
        vp_uri,
        bob_cred,
        "bob",
        {"credentialUri": bob_cred, "notesHash": digest("inspection-plan.md")},
    )
    assertions.expect_ok("value proposition validation", reply)

    def claim(label: str, with_vp: bool = True) -> tuple[str, str]:
        request = {
            "work": {
                "titleHash": digest("statement-of-work.md"),
                "discipline": "structural",
                "jurisdiction": "US-TX",
                "projectRef": "cedar-crossing-deck-2026",
            },
            "selectionCriteria": CRITERIA,
            "selectionCriteriaHash": hash_text(json.dumps(CRITERIA, sort_keys=True)),
            "statementHash": digest("inspection-plan.md"),
            "definitionHash": digest("statement-of-work.md"),
            "quantity": {"unit": "bay-inspections", "value": 12},
            "evidence": [{"kind": "inspection-plan", "hash": digest("inspection-plan.md")}],
            "valuePropositionRef": {"id": vp_uri, "uri": vp_uri} if with_vp else None,
            "deadlineHeight": height + 100_000,
            "commentUntilHeight": height + 50_000,
        }
        created = fixtures.claim("alice", request)
        assertions.expect_ok(f"{label} claim", created)
        claim_uri = created[1]["uri"]
        validation = {
            "verdict": "valid",
            "quality": {"completeness": 5, "correctness": 5, "traceability": 5, "fitness": 5},
            "credentialUri": bob_cred,
            "characteristicsHash": digest("inspection-report.md"),
            "commentHash": hash_text("validated against inspection plan revision C"),
            "evidence": [{"kind": "inspection-report", "hash": digest("inspection-report.md")}],
        }
        validated = fixtures.claim_validate(claim_uri, bob_cred, "bob", validation)
        assertions.expect_ok(f"{label} claim validation", validated)
        return claim_uri, validated[1]["uri"]

    def approve(kasset_uri: str, label: str) -> None:
        approval = {
            "decision": "approve",
            "conditionsHash": hash_text("liability follows the approval basis"),
            "credentialUri": carol_cred,
            "liability": {
                "responsible": carol,
                "shareBps": 10_000,
                "basisHash": digest("terms.md"),
            },
        }
        reply = fixtures.kasset_approve(kasset_uri, carol_cred, "carol", approval)
        assertions.expect_ok(f"{label} K-Asset approval", reply)

    claim_a, kasset_a = claim("approved")
    approve(kasset_a, "approved")

    claim_b, kasset_b = claim("disputed")
    approve(kasset_b, "disputed")
    case_req = {
        "kind": "dispute",
        "openedBy": alice,
        "parties": [alice, bob],
        "groundsHash": digest("dispute-grounds.md"),
        "requirement": ORACLE_REQUIREMENT,
        "adjudicator": dave,
        "adjudicatorCredentialUri": dave_cred,
        "deadlineHeight": height + 100_000,
    }
    opened = fixtures.kasset_open_dispute(kasset_b, "alice", case_req)
    assertions.expect_ok("dispute case", opened)
    case_uri = opened[1]["uri"]
    decision = {
        "outcome": "uphold",
        "liability": {"responsible": carol, "shareBps": 10_000, "basisHash": digest("terms.md")},
        "conditionsHash": hash_text("validated report revision C stands"),
        "rationaleHash": digest("oracle-rationale.md"),
    }
    reply = fixtures.oracle_decide(case_uri, "dave", decision)
    assertions.expect_ok("oracle decision", reply)
    reply = fixtures.oracle_execute(case_uri)
    assertions.expect_ok("oracle execution", reply)

    prov = fixtures.provenance_create(
        {"type": "kasset", "id": kasset_a, "uri": kasset_a}, [alice, bob, carol]
    )
    assertions.expect_ok("provenance", prov)
    prov_uri = prov[1]["uri"]
    report_hash = digest("inspection-report.md")
    reply = fixtures.provenance_anchor(
        prov_uri,
        "alice",
        {"kind": "inspection-report", "hash": report_hash, "parentHash": ""},
    )
    assertions.expect_ok("report anchor", reply)
    reply = fixtures.provenance_anchor(
        prov_uri,
        "alice",
        {"kind": "photo-log", "hash": digest("photo-log.md"), "parentHash": report_hash},
    )
    assertions.expect_ok("photo-log anchor", reply)
    reply = fixtures.provenance_comment(
        prov_uri, "alice", {"hash": hash_text("photo set complete for all twelve bays")}
    )
    assertions.expect_ok("provenance comment", reply)

    status = node.http_json("GET", f"{node.NODE}/api/v1/status")
    manifest = json.loads(node.MANIFEST.read_text())
    catalogue = {
        "networkId": status.get("networkId"),
        "shard": status.get("shardId"),
        "root": manifest["root_uri"],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "entries": [
            {"kind": "identity", "uri": identities[name], "label": f"{name} identity",
             "detail": actors.address(name)}
            for name in ("alice", "bob", "carol", "dave")
        ]
        + [
            {"kind": "credential", "uri": bob_cred, "label": "Bob · Validator"},
            {"kind": "credential", "uri": carol_cred, "label": "Carol · Approver"},
            {"kind": "credential", "uri": dave_cred, "label": "Dave · Oracle"},
            {"kind": "value", "uri": vp_uri, "label": "Cedar Crossing value proposition"},
            {"kind": "claim", "uri": claim_a, "label": "Approved claim · twelve bays"},
            {"kind": "kasset", "uri": kasset_a, "label": "Approved K-Asset"},
            {"kind": "claim", "uri": claim_b, "label": "Disputed claim · twelve bays"},
            {"kind": "kasset", "uri": kasset_b, "label": "Upheld K-Asset"},
            {"kind": "case", "uri": case_uri, "label": "Cedar Crossing dispute"},
            {"kind": "provenance", "uri": prov_uri, "label": "Inspection provenance"},
        ],
    }
    args.catalogue.parent.mkdir(parents=True, exist_ok=True)
    args.catalogue.write_text(json.dumps(catalogue, indent=2) + "\n")

    keys = node.keys_path()
    keystores = {
        label: build_keystore(name, label, keys, args.keystores, args.password)
        for name, label in (
            ("deployer", "issuer"),
            ("alice", "alice"),
            ("bob", "bob"),
            ("carol", "carol"),
            ("dave", "dave"),
        )
    }
    seed = {
        "network": args.net,
        "networkId": status.get("networkId"),
        "shard": status.get("shardId"),
        "root": manifest["root_uri"],
        "actors": {"alice": alice, "bob": bob, "carol": carol, "dave": dave},
        "credentials": {"validator": bob_cred, "approver": carol_cred, "oracle": dave_cred},
        "claimApproved": claim_a,
        "kassetApproved": kasset_a,
        "claimDisputed": claim_b,
        "kassetDisputed": kasset_b,
        "case": case_uri,
        "valueProposition": vp_uri,
        "provenance": prov_uri,
        "keystorePassword": args.password,
        "keystores": {label: str(path) for label, path in keystores.items()},
    }
    (ROOT / ".demo").mkdir(exist_ok=True)
    (ROOT / ".demo" / f"seed-{args.net}.json").write_text(json.dumps(seed, indent=2) + "\n")

    print("demo_seed: ok")
    print(f"  approved K-Asset {kasset_a}")
    print(f"  disputed K-Asset {kasset_b}")
    print(f"  case {case_uri}")
    print(f"  catalogue {args.catalogue}")
    print(f"  keystores {args.keystores} (password: {args.password})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
