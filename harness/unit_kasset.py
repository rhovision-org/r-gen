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

    reply = fixtures.kasset_prove_approved(kasset_uri, "alice")
    assertions.expect("proveApproved returns proof and take", isinstance(reply, list), True)
    prove, take = reply
    assertions.expect_ok("proveApproved", prove)
    assertions.expect_ok("approval proof take", take)
    assertions.expect("approval proof id", take[1].get("id"), kasset_uri)

    # A claimant cannot approve.
    claim2, kasset2, _ = suite_base.validated_kasset(addrs, "bob")
    reply = fixtures.kasset_approve(kasset2, alice_cred, "alice",
                                    suite_base.approval(alice_cred, addrs["alice"]))
    assertions.expect_refusal("claimant approval refused", reply, "conflict")

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
    _, oc1 = suite_base.approved_kasset(addrs, "bob", "carol")
    _, oc2 = suite_base.approved_kasset(addrs, "bob", "carol")
    _, oparent = suite_base.approved_kasset(addrs, "bob", "carol")
    reply = fixtures.kasset_nest(oparent, "alice",
                                 list(reversed([{"id": oc1, "uri": oc1},
                                                {"id": oc2, "uri": oc2}])))
    assertions.expect_refusal("unsorted children refused", reply, "order")
    reply = fixtures.kasset_nest(parent, "bob", refs)
    assertions.expect_refusal("non-claimant nest refused", reply, "not claimant")

    # Nest on a validated but not approved parent.
    claim5, kasset5, _ = suite_base.validated_kasset(addrs, "bob")
    reply = fixtures.kasset_nest(kasset5, "alice", refs)
    assertions.expect_refusal("unapproved parent refused", reply, "parent not approved")

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

    print("unit_kasset: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
