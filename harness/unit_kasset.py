#!/usr/bin/env python3
"""K-Asset primitive: approve, reject, proveApproved, two-phase nest, dispute."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import assertions
import corpus
import fixtures
import suite_base


def main() -> int:
    if not suite_base.require("unit_kasset"):
        return 2
    addrs = suite_base.setup(("alice", "bob", "carol", "dave"))
    carol_cred = suite_base.issue(addrs, "carol", "Approver", "approver")
    alice_cred = suite_base.issue(addrs, "alice", "Approver", "approver")

    claim_uri, kasset_uri = suite_base.approved_kasset(addrs, "bob", "carol")
    reply = fixtures.read(kasset_uri, "get")
    assertions.expect("K-Asset approved", reply[1].get("status"), "approved")
    assertions.expect("K-Asset id set", reply[1].get("id"), kasset_uri)

    # Conformance fixture for kasset.conventions/v1: quality 3 across four dimensions,
    # valid verdict, approved, full liability. The convention rate is 4000 bps.
    quality3 = {"completeness": 3, "correctness": 3,
                "traceability": 3, "fitness": 3}
    _, fixture_kasset, _ = suite_base.validated_kasset(addrs, "bob", quality=quality3)
    reply = fixtures.kasset_approve(fixture_kasset, carol_cred, "carol",
                                    suite_base.approval(carol_cred, addrs["carol"]))
    assertions.expect_ok("convention fixture approved", reply)
    state = fixtures.read(fixture_kasset, "get")[1]
    assertions.expect("convention quantity", state.get("quantity"),
                      {"unit": "inspections", "value": 12})
    assertions.expect("convention quality", state.get("quality"), quality3)
    assertions.expect("convention verdict", state.get("verdict"), "valid")
    assertions.expect("convention status", state.get("status"), "approved")
    liability = state.get("approval", {}).get("liability", {})
    assertions.expect("convention liability share", liability.get("shareBps"), 10000)
    quality_sum = sum(quality3.values())
    engineering_bps = (20 - quality_sum) * 500
    assertions.expect("convention engineering rate", engineering_bps, 4000)

    reply = fixtures.kasset_prove_approved(kasset_uri, "alice")
    assertions.expect("proveApproved returns proof and take", isinstance(reply, list), True)
    prove, take = reply
    assertions.expect_ok("proveApproved", prove)
    corpus.assert_row("KASSET-proveApproved", prove)
    assertions.expect_ok("approval proof take", take)
    assertions.expect("approval proof id", take[1].get("id"), kasset_uri)

    # proveApproved is permissionless, but the proof is the K-Asset's own data:
    # a third party cannot choose a different target (RGA-040).
    reply = fixtures.kasset_prove_approved(kasset_uri, "bob")
    prove, take = reply
    assertions.expect_ok("third-party proveApproved", prove)
    assertions.expect_ok("third-party proof take", take)
    assertions.expect("third-party proof target", take[1].get("id"), kasset_uri)

    # A claimant cannot approve.
    claim2, kasset2, _ = suite_base.validated_kasset(addrs, "bob")
    reply = fixtures.kasset_approve(kasset2, alice_cred, "alice",
                                    suite_base.approval(alice_cred, addrs["alice"]))
    assertions.expect_refusal("claimant approval refused", reply, "conflict")
    corpus.assert_row("K1-approve-self", reply)

    # A forged credential is refused.
    claim3, kasset3, _ = suite_base.validated_kasset(addrs, "bob")
    reply = fixtures.kasset_approve(kasset3, fixtures.fake_uri(), "carol",
                                    suite_base.approval("forged", addrs["carol"]))
    assertions.expect_refusal("forged approval credential", reply, "forged credential")

    # Reject.
    claim4, kasset4, _ = suite_base.validated_kasset(addrs, "bob")
    reply = fixtures.kasset_reject(kasset4, carol_cred, "carol",
                                   suite_base.approval(carol_cred, addrs["carol"]))
    assertions.expect_ok("reject K-Asset", reply)
    corpus.assert_row("KASSET-reject", reply)
    assertions.expect("K-Asset rejected", fixtures.read(kasset4, "get")[1].get("status"),
                      "rejected")

    # Nest: two children approved before the parent.
    _, child1 = suite_base.approved_kasset(addrs, "bob", "carol")
    _, child2 = suite_base.approved_kasset(addrs, "bob", "carol")
    _, parent = suite_base.approved_kasset(addrs, "bob", "carol")
    refs = [{"id": child1, "uri": child1}, {"id": child2, "uri": child2}]
    reply = fixtures.kasset_nest(parent, "alice", refs)
    assertions.expect_ok("nest children", reply)
    stored = fixtures.read(parent, "children")[1]
    assertions.expect("two children stored", len(stored), 2)
    reply = fixtures.kasset_nest(parent, "alice", [refs[0]])
    assertions.expect_refusal("duplicate child refused", reply, "duplicate child")
    reply = fixtures.kasset_resume_nest(parent, "alice")
    assertions.expect_refusal("resume without receipt refused", reply, "no receipt")
    reply = fixtures.kasset_abort_nest(parent, "alice")
    assertions.expect_refusal("abort without receipt refused", reply, "no receipt")

    # An unsorted batch passes the read-only preflight (each child is approved and
    # older than the parent), reserves the parent, records the first proof, then
    # fails on ascending order. The receipt must remain for resume or abort, and a
    # second nest must not start over the reserved parent.
    _, oc1 = suite_base.approved_kasset(addrs, "bob", "carol")
    _, oc2 = suite_base.approved_kasset(addrs, "bob", "carol")
    _, oparent = suite_base.approved_kasset(addrs, "bob", "carol")
    unsorted = [{"id": oc2, "uri": oc2}, {"id": oc1, "uri": oc1}]
    sorted_refs = [{"id": oc1, "uri": oc1}, {"id": oc2, "uri": oc2}]
    reply = fixtures.kasset_nest(oparent, "alice", unsorted)
    assertions.expect_refusal("unsorted children refused", reply, "order")
    corpus.assert_row("K3-nest-unsorted", reply)
    reply = fixtures.kasset_nest(oparent, "alice", sorted_refs)
    assertions.expect_refusal("second nest refused while receipt held", reply,
                              "nest in progress")
    state = fixtures.read(oparent, "get")[1]
    assertions.expect("nest receipt records the partial batch",
                      state.get("nestReceipt") is not None, True)
    assertions.expect("nest receipt records both consumed proofs",
                      len(state.get("nestReceipt").get("taken")), 2)
    reply = fixtures.kasset_resume_nest(oparent, "alice")
    assertions.expect_refusal("resume keeps the recorded prefix and order", reply,
                              "order")
    reply = fixtures.kasset_abort_nest(oparent, "alice")
    assertions.expect_ok("abort clears the nest receipt", reply)
    assertions.expect("abort leaves no receipt",
                      fixtures.read(oparent, "get")[1].get("nestReceipt"), None)
    reply = fixtures.kasset_nest(oparent, "alice", sorted_refs)
    assertions.expect_ok("nest after abort", reply)
    assertions.expect("two children after abort",
                      len(fixtures.read(oparent, "children")[1]), 2)
    reply = fixtures.kasset_nest(parent, "bob", refs)
    assertions.expect_refusal("non-claimant nest refused", reply, "not claimant")

    # Nest on a validated but not approved parent.
    claim5, kasset5, _ = suite_base.validated_kasset(addrs, "bob")
    reply = fixtures.kasset_nest(kasset5, "alice", refs)
    assertions.expect_refusal("unapproved parent refused", reply, "parent not approved or limit")

    # An approval is a durable transition; revoking the approver's credential does
    # not de-approve the K-Asset (RGA-055, accepted).
    _, rev_kasset, _ = suite_base.validated_kasset(addrs, "bob")
    rev_cred = suite_base.issue(addrs, "carol", "Approver", "approver")
    reply = fixtures.kasset_approve(rev_kasset, rev_cred, "carol",
                                    suite_base.approval(rev_cred, addrs["carol"]))
    assertions.expect_ok("approve before revocation", reply)
    reply = fixtures.revoke_credential(rev_cred, "carol")
    assertions.expect_ok("revoke approver credential", reply)
    assertions.expect("approval survives revocation",
                      fixtures.read(rev_kasset, "get")[1].get("status"), "approved")

    # Dispute parties.
    case_req = {
        "kind": "dispute",
        "groundsHash": "grounds",
        "adjudicator": addrs["dave"],
        "adjudicatorCredentialUri": suite_base.issue(addrs, "dave", "Oracle", "oracle"),
        "deadlineHeight": 1000000,
    }
    reply = fixtures.kasset_open_dispute(kasset_uri, "dave", case_req)
    assertions.expect_refusal("non-party dispute refused", reply, "not a party")
    reply = fixtures.kasset_open_dispute(kasset_uri, "alice", case_req)
    assertions.expect_ok("party dispute", reply)
    corpus.assert_row("KASSET-openDispute-party", reply)

    print("unit_kasset: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
