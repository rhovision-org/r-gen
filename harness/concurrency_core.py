#!/usr/bin/env python3
"""Behavioural regression suite for the Pareto core.

This suite is evidence only. Race non-representability is proved by
`RGen.core_races_not_representable` in `spec/lean`; do not cite this file as the proof.

Each test puts two or more calls in ONE deploy with parallel processes. The per-entity
linear cell serializes them; the loser observes the post-state and must refuse. The
independent-claim test puts eight different claim cells in one deploy and requires all
eight to succeed.
"""

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
FRANK = "frank"


def approved_one():
    claim_uri = fixtures.claim(ALICE, claim_req())[1]["uri"]
    cred = fixtures.issue(actors.address(BOB), "Validator", "structural", "US-TX",
                          "validator", 1)[1]
    val = fixtures.claim_validate(claim_uri, cred, BOB,
                                  {"verdict": "valid",
                                   "quality": {"completeness": 5, "correctness": 5,
                                               "traceability": 5, "fitness": 5},
                                   "credentialUri": cred, "characteristicsHash": "c",
                                   "commentHash": "c", "evidence": []})
    kasset = val[1]["uri"]
    approver = fixtures.issue(actors.address(CAROL), "Approver", "structural", "US-TX",
                              "approver", 1)[1]
    fixtures.kasset_approve(kasset, approver, CAROL,
                            {"decision": "approve", "conditionsHash": "",
                             "credentialUri": approver,
                             "liability": {"responsible": carol_placeholder(),
                                           "shareBps": 10000,
                                           "basisHash": "l"}})
    return claim_uri, kasset


def carol_placeholder():
    return actors.address(CAROL)


def suite_base_approved():
    return approved_one()


def split(replies):
    ok = [r for r in replies if isinstance(r, tuple) and r[0] is True]
    bad = [r for r in replies if isinstance(r, tuple) and r[0] is False]
    return ok, bad


def claim_req():
    req = fixtures.claim_req(ALICE)
    req["deadlineHeight"] = 1000000
    req["commentUntilHeight"] = 1000000
    return req


def main() -> int:
    if not preflight.require_devnet("concurrency_core"):
        return 2
    for name in (ALICE, BOB, CAROL, DAVE, FRANK):
        actors.ensure_vault(name)

    alice = actors.address(ALICE)
    bob = actors.address(BOB)
    carol = actors.address(CAROL)
    dave = actors.address(DAVE)
    frank = actors.address(FRANK)
    suffix = uuid.uuid4().hex[:8]

    for name in (ALICE, BOB, CAROL, DAVE, FRANK):
        assertions.expect_ok(f"{name} identity",
                             fixtures.ensure_identity(name, f"{name}-{suffix}"))

    bob_cred = fixtures.issue(bob, "Validator", "structural", "US-TX", "validator", 1)[1]
    carol_cred = fixtures.issue(carol, "Approver", "structural", "US-TX", "approver", 1)[1]
    dave_cred = fixtures.issue(dave, "Oracle", "structural", "US-TX", "oracle", 1)[1]
    frank_cred = fixtures.issue(frank, "Validator", "structural", "US-TX", "validator", 1)[1]

    validation = {
        "verdict": "valid",
        "quality": {"completeness": 5, "correctness": 5,
                    "traceability": 5, "fitness": 5},
        "credentialUri": bob_cred,
        "characteristicsHash": "chars",
        "commentHash": "comments",
        "evidence": [],
    }
    approval = {
        "decision": "approve",
        "conditionsHash": "",
        "credentialUri": carol_cred,
        "liability": {"responsible": carol, "shareBps": 10000, "basisHash": "liability"},
    }

    # 1. Two validations of the same claim in one deploy: exactly one wins.
    claim = fixtures.claim(ALICE, claim_req())
    assertions.expect_ok("race claim created", claim)
    replies = fixtures.two_claim_validations(claim[1]["uri"], bob_cred, BOB, validation)
    ok, bad = split(replies)
    assertions.expect("one validation wins", len(ok), 1)
    assertions.expect("one validation refuses", len(bad), 1)
    assertions.expect("loser sees not open", bad[0][1], "not open")
    race_kasset = ok[0][1]["uri"]

    # 2. Two approvals of the same K-Asset: exactly one wins.
    replies = fixtures.two_kasset_approvals(race_kasset, carol_cred, CAROL, approval)
    ok, bad = split(replies)
    assertions.expect("one approval wins", len(ok), 1)
    assertions.expect("one approval refuses", len(bad), 1)
    assertions.expect("loser sees not validated", bad[0][1], "not validated")

    # 3. Two executes of the same case: exactly one applies the decision.
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
    opened = fixtures.kasset_open_dispute(race_kasset, ALICE, case_req)
    assertions.expect_ok("race dispute opened", opened)
    case_uri = opened[1]["uri"]
    decision = {
        "outcome": "uphold",
        "liability": {"responsible": carol, "shareBps": 10000, "basisHash": "oracle"},
        "conditionsHash": "",
        "rationaleHash": "rationale",
    }
    assertions.expect_ok("race case decided",
                         fixtures.oracle_decide(case_uri, DAVE, decision))
    replies = fixtures.two_oracle_executes(case_uri)
    applied = [r for r in replies if isinstance(r, tuple) and r == (True, "upheld")]
    assertions.expect("exactly one apply", len(applied), 1)
    reply = fixtures.read(race_kasset, "get")
    assertions.expect("K-Asset upheld once", reply[1].get("status"), "upheld")

    # 4. Cross-subject isolation: a decision on A leaves B untouched.
    def approved(claim_uri):
        kasset = fixtures.claim_validate(claim_uri, bob_cred, BOB, validation)[1]["uri"]
        fixtures.kasset_approve(kasset, carol_cred, CAROL, approval)
        return kasset

    a = approved(fixtures.claim(ALICE, claim_req())[1]["uri"])
    b = approved(fixtures.claim(ALICE, claim_req())[1]["uri"])
    opened = fixtures.kasset_open_dispute(a, ALICE, case_req)
    case_a = opened[1]["uri"]
    fixtures.oracle_decide(case_a, DAVE, decision)
    fixtures.oracle_execute(case_a)
    reply = fixtures.read(a, "get")
    assertions.expect("A upheld", reply[1].get("status"), "upheld")
    reply = fixtures.read(b, "get")
    assertions.expect("B untouched", reply[1].get("status"), "approved")

    # 5. Two comments on one claim both append; no lost update.
    comment_claim = fixtures.claim(ALICE, claim_req())[1]["uri"]
    replies = fixtures.two_comments(comment_claim, ALICE, {"hash": "comment"})
    ok, bad = split(replies)
    assertions.expect("both comments accepted", len(ok), 2)
    reply = fixtures.read(comment_claim, "comments")
    assertions.expect("both comments stored", len(reply[1]), 2)

    # 6. Eight independent claims validate in one deploy: all succeed.
    claims = [fixtures.claim(ALICE, claim_req())[1]["uri"] for _ in range(8)]
    replies = fixtures.n_claim_validations(claims, bob_cred, BOB, validation)
    assertions.expect("eight independent validations", len(replies), 8)
    assertions.expect("all eight succeed",
                      all(isinstance(r, tuple) and r[0] is True for r in replies), True)

    # 7. A revoked credential cannot validate a new claim.
    revoke = fixtures.call_uri(fixtures.comp("credential-factory"), "verify",
                               [frank_cred], deployer=False)
    assertions.expect_ok("frank credential issued", revoke)
    reply = fixtures.call_uri(frank_cred, "revoke", [__import__("terms").Raw("*dId"),
                                                     "race"], key=FRANK)
    assertions.expect_ok("frank credential revoked", reply)
    late = fixtures.claim(ALICE, claim_req())[1]["uri"]
    reply = fixtures.claim_validate(late, frank_cred, FRANK,
                                     dict(validation, credentialUri=frank_cred))
    assertions.expect_refusal("revoked credential refused", reply, "proof")

    # 8. Prove vs revoke on the same credential: revoke wins, the proof may be taken
    # before the revoke and remains valid (non-retroactive).
    bob2 = fixtures.issue(bob, "Validator", "structural", "US-TX", "validator", 1)[1]
    race_req = {"ctype": "Validator", "discipline": "structural",
                "jurisdiction": "US-TX", "role": "validator", "minLevel": 1}
    race = fixtures.cred_prove_vs_revoke(bob2, BOB, race_req)
    prove, revoke = race[0], race[1]
    take = race[2] if len(race) > 2 else None
    assertions.expect_ok("race revoke", revoke)
    assertions.expect("prove is some or refused",
                      isinstance(prove, tuple) and (prove[0] is True or prove[0] is False),
                      True)
    if isinstance(take, tuple) and take and take[0] is True:
        assertions.expect("pre-revoke proof remains valid", take[1].get("subject"), bob)
    late = fixtures.cred_prove(bob2, BOB, race_req)
    assertions.expect_refusal("prove after race refused", late, "revoked")

    # 9. proveValidated vs dispute on the same VP.
    vp = fixtures.vp_propose(ALICE, {
        "subjectRef": {"type": "claim", "id": "pending", "uri": ""},
        "statementHash": "race-vp", "valueModelHash": "m",
        "beneficiaries": [alice], "termsHash": "t",
        "selectionCriteria": {"ctype": "Validator", "discipline": "structural",
                              "jurisdiction": "US-TX", "role": "validator", "minLevel": 1},
        "deadlineHeight": 1000000,
    })
    assertions.expect_ok("race VP", vp)
    vp_uri = vp[1]["uri"]
    bob3 = fixtures.issue(bob, "Validator", "structural", "US-TX", "validator", 1)[1]
    fixtures.vp_validate(vp_uri, bob3, BOB, {"credentialUri": bob3, "notesHash": "n"})
    race_case = dict(case_req, adjudicator=dave, adjudicatorCredentialUri=dave_cred)
    race_vp = fixtures.vp_prove_vs_dispute(vp_uri, ALICE, race_case)
    p2, d2 = race_vp[0], race_vp[1]
    t2 = race_vp[2] if len(race_vp) > 2 else None
    assertions.expect_ok("race dispute", d2)
    if isinstance(t2, tuple) and t2 and t2[0] is True:
        assertions.expect("pre-dispute proof remains valid", t2[1].get("caller"), alice)
    late_vp = fixtures.vp_prove_validated(vp_uri, ALICE)
    assertions.expect_refusal("prove after dispute refused", late_vp, "not validated")

    # 10. decide vs expire on the same oracle case: exactly one wins.
    _, race_kasset2 = suite_base_approved()
    opened = fixtures.kasset_open_dispute(race_kasset2, ALICE, case_req)
    assertions.expect_ok("race case opened", opened)
    d3, e3 = fixtures.oracle_decide_vs_expire(opened[1]["uri"], DAVE, decision)
    wins = [r for r in (d3, e3) if isinstance(r, tuple) and r[0] is True]
    assertions.expect("exactly one of decide/expire", len(wins), 1)

    # 11. Two identity creates for one address: exactly one wins. Use a key that
    # has no identity yet, so reruns against a persistent devnet stay meaningful.
    fresh = None
    for candidate in ("ida", "idb", "wa", "wb", "ka", "kb", "kc", "ta", "tb", "tc"):
        actors.ensure_vault(candidate)
        lookup = fixtures.call_uri(fixtures.comp("identity-directory"), "lookup",
                                   [actors.address(candidate)], deployer=False)
        if not (isinstance(lookup, tuple) and lookup and lookup[0] is True):
            fresh = candidate
            break
    if fresh is None:
        print("  skip one identity create wins: no fresh key")
    else:
        a1, a2 = fixtures.two_identity_creates(fresh, f"{fresh}-race")
        winners = [r for r in (a1, a2) if isinstance(r, tuple) and r[0] is True]
        assertions.expect("one identity create wins", len(winners), 1)

    # 12. Two nests of the same child into one parent: exactly one wins.
    _, nc1 = approved_one()
    _, np1 = approved_one()
    refs1 = [{"id": nc1, "uri": nc1}]
    n1, n2 = fixtures.two_nests_same_parent(np1, ALICE, refs1)
    nwins = [r for r in (n1, n2) if isinstance(r, tuple) and r[0] is True]
    assertions.expect("one nest wins", len(nwins), 1)

    print("concurrency_core: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
