#!/usr/bin/env python3
"""Pareto core vertical slice: identity -> credential -> value proposition -> claim ->
validation -> K-Asset -> approval -> dispute -> oracle -> provenance."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import actors
import assertions
import fixtures
import preflight

ALICE = "alice"
BOB = "bob"
CAROL = "carol"
DAVE = "dave"


def main() -> int:
    if not preflight.require_devnet("unit_core"):
        return 2
    for name in (ALICE, BOB, CAROL, DAVE):
        actors.ensure_vault(name)

    alice = actors.address(ALICE)
    bob = actors.address(BOB)
    carol = actors.address(CAROL)
    dave = actors.address(DAVE)
    suffix = uuid.uuid4().hex[:8]

    assertions.expect_ok("alice identity",
                         fixtures.ensure_identity(ALICE, f"alice-{suffix}"))
    assertions.expect_ok("bob identity",
                         fixtures.ensure_identity(BOB, f"bob-{suffix}"))
    assertions.expect_ok("carol identity",
                         fixtures.ensure_identity(CAROL, f"carol-{suffix}"))
    assertions.expect_ok("dave identity",
                         fixtures.ensure_identity(DAVE, f"dave-{suffix}"))

    validator = fixtures.issue(bob, "Validator", "structural", "US-TX", "validator", 1)
    assertions.expect_ok("validator credential", validator)
    bob_cred = validator[1]

    approver = fixtures.issue(carol, "Approver", "structural", "US-TX", "approver", 1)
    assertions.expect_ok("approver credential", approver)
    carol_cred = approver[1]

    oracle_cred = fixtures.issue(dave, "Oracle", "structural", "US-TX", "oracle", 1)
    assertions.expect_ok("oracle credential", oracle_cred)
    dave_cred = oracle_cred[1]

    vp_req = {
        "subjectRef": {"type": "claim", "id": "pending", "uri": ""},
        "statementHash": "vp-statement",
        "valueModelHash": "vp-model",
        "beneficiaries": [alice],
        "termsHash": "vp-terms",
        "selectionCriteria": {"ctype": "Validator", "discipline": "structural",
                              "jurisdiction": "US-TX", "role": "validator", "minLevel": 1},
        "deadlineHeight": 1000000,
        **fixtures.vp_asset(),
    }
    vp = fixtures.vp_propose(ALICE, vp_req)
    assertions.expect_ok("propose value proposition", vp)
    vp_uri = vp[1]["uri"]

    reply = fixtures.vp_validate(vp_uri, bob_cred, BOB,
                                 {"credentialUri": bob_cred, "notesHash": "vp-notes"})
    assertions.expect_ok("validate value proposition", reply)

    req = fixtures.claim_req(ALICE, value_proposition={"id": vp_uri, "uri": vp_uri})
    req["deadlineHeight"] = 1000000
    req["commentUntilHeight"] = 1000000
    claim = fixtures.claim(ALICE, req)
    assertions.expect_ok("create claim", claim)
    claim_uri = claim[1]["uri"]

    validation = {
        "verdict": "valid",
        "quality": {"completeness": 5, "correctness": 5,
                    "traceability": 5, "fitness": 5},
        "credentialUri": bob_cred,
        "characteristicsHash": "chars",
        "commentHash": "comments",
        "evidence": [{"kind": "report", "hash": "dd"}],
    }
    validated = fixtures.claim_validate(claim_uri, bob_cred, BOB, validation)
    assertions.expect_ok("validate claim", validated)
    kasset_uri = validated[1]["uri"]

    approval = {
        "decision": "approve",
        "conditionsHash": "",
        "credentialUri": carol_cred,
        "liability": {"responsible": carol, "shareBps": 10000, "basisHash": "liability"},
    }
    reply = fixtures.kasset_approve(kasset_uri, carol_cred, CAROL, approval)
    assertions.expect_ok("approve K-Asset", reply)

    reply = fixtures.read(kasset_uri, "get")
    assertions.expect_ok("K-Asset read", reply)
    assertions.expect("K-Asset approved", reply[1].get("status"), "approved")
    assertions.expect("K-Asset has approval version", reply[1].get("approvalVersion"), 2)

    case_req = {
        "kind": "dispute",
        "openedBy": alice,
        "parties": [alice, bob],
        "groundsHash": "grounds",
        "requirement": {"ctype": "Oracle", "discipline": "structural",
                        "jurisdiction": "US-TX", "role": "oracle", "minLevel": 1},
        "adjudicator": dave,
        "adjudicatorCredentialUri": dave_cred,
        "deadlineHeight": 1000000,
    }
    opened = fixtures.kasset_open_dispute(kasset_uri, ALICE, case_req)
    assertions.expect_ok("open dispute", opened)
    case_uri = opened[1]["uri"]

    decision = {
        "outcome": "uphold",
        "liability": {"responsible": carol, "shareBps": 10000, "basisHash": "oracle"},
        "conditionsHash": "",
        "rationaleHash": "rationale",
    }
    reply = fixtures.oracle_decide(case_uri, DAVE, decision)
    assertions.expect_ok("oracle decide", reply)

    reply = fixtures.oracle_execute(case_uri)
    assertions.expect_ok("oracle execute", reply)
    reply = fixtures.read(kasset_uri, "get")
    assertions.expect("K-Asset upheld", reply[1].get("status"), "upheld")

    prov = fixtures.provenance_create(kasset_uri, [alice, bob])
    assertions.expect_ok("create provenance", prov)
    prov_uri = prov[1]["uri"]
    reply = fixtures.provenance_anchor(prov_uri, ALICE,
                                       {"kind": "inspection", "hash": "aa", "parentHash": ""})
    assertions.expect_ok("anchor provenance", reply)
    reply = fixtures.read(prov_uri, "verify", ["aa"])
    assertions.expect("verify anchor", reply, (True, True))

    print("unit_core: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
