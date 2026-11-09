#!/usr/bin/env python3
"""Integration: VP-linked claim, approval with both proofs, dispute, rejection, recovery."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import assertions
import fixtures
import suite_base


def main() -> int:
    if not suite_base.require("integration_core"):
        return 2
    addrs = suite_base.setup(("alice", "bob", "carol", "dave"))
    bob_cred = suite_base.issue(addrs, "bob", "Validator", "validator")
    carol_cred = suite_base.issue(addrs, "carol", "Approver", "approver")
    selection = suite_base.requirement("Validator", "validator")

    vp = fixtures.vp_propose("alice", {
        "subjectRef": {"type": "claim", "id": "pending", "uri": ""},
        "statementHash": f"vp-{uuid.uuid4().hex[:6]}",
        "valueModelHash": "model",
        "beneficiaries": [addrs["alice"]],
        "termsHash": "terms",
        "selectionCriteria": selection,
        "deadlineHeight": 1000000,
        **fixtures.vp_asset(),
    })
    assertions.expect_ok("propose VP", vp)
    vp_uri = vp[1]["uri"]
    assertions.expect_ok("validate VP",
                         fixtures.vp_validate(vp_uri, bob_cred, "bob",
                                              {"credentialUri": bob_cred,
                                               "notesHash": "notes"}))

    claim = fixtures.claim("alice", suite_base.claim_req(addrs["alice"], vp_uri))
    assertions.expect_ok("create claim", claim)
    claim_uri = claim[1]["uri"]
    validated = fixtures.claim_validate(claim_uri, bob_cred, "bob",
                                        suite_base.validation(bob_cred))
    assertions.expect_ok("validate claim", validated)
    kasset_uri = validated[1]["uri"]
    kasset = fixtures.read(kasset_uri, "get")[1]
    assertions.expect("K-Asset carries the VP variance snapshot",
                      kasset.get("variance").get("quantityBps"), 400)
    assertions.expect("K-Asset variance traces to the VP",
                      kasset.get("valuePropositionRef").get("uri"), vp_uri)

    reply = fixtures.kasset_approve(kasset_uri, carol_cred, "carol",
                                    suite_base.approval(carol_cred, addrs["carol"]))
    assertions.expect_ok("approve with credential and VP proofs", reply)
    assertions.expect("approved", fixtures.read(kasset_uri, "get")[1].get("status"),
                      "approved")

    case_req = {
        "kind": "dispute",
        "groundsHash": "grounds",
        "adjudicator": addrs["dave"],
        "adjudicatorCredentialUri": suite_base.issue(addrs, "dave", "Oracle", "oracle"),
        "deadlineHeight": 1000000,
    }
    opened = fixtures.kasset_open_dispute(kasset_uri, "alice", case_req)
    assertions.expect_ok("open dispute", opened)
    decision = {"outcome": "uphold", "rationaleHash": "rationale"}
    assertions.expect_ok("decide", fixtures.oracle_decide(opened[1]["uri"], "dave",
                                                          decision))
    assertions.expect_ok("execute", fixtures.oracle_execute(opened[1]["uri"]))
    assertions.expect("upheld", fixtures.read(kasset_uri, "get")[1].get("status"),
                      "upheld")

    # Rejection path.
    bad = fixtures.claim("alice", suite_base.claim_req(addrs["alice"]))
    assertions.expect_ok("rejection claim", bad)
    rejected = fixtures.claim_validate(bad[1]["uri"], bob_cred, "bob",
                                       suite_base.validation(bob_cred, "invalid"))
    assertions.expect_ok("invalid validation", rejected)
    reply = fixtures.kasset_approve(rejected[1]["uri"], carol_cred, "carol",
                                    suite_base.approval(carol_cred, addrs["carol"]))
    assertions.expect_refusal("rejected K-Asset cannot approve", reply, "not validated")

    # Revocation then re-issue.
    assertions.expect_ok("revoke validator", fixtures.revoke_credential(bob_cred, "bob"))
    blocked = fixtures.claim("alice", suite_base.claim_req(addrs["alice"]))
    assertions.expect_ok("blocked claim", blocked)
    reply = fixtures.claim_validate(blocked[1]["uri"], bob_cred, "bob",
                                    suite_base.validation(bob_cred))
    assertions.expect_refusal("revoked credential blocks validation", reply, "proof")
    fresh = suite_base.issue(addrs, "bob", "Validator", "validator")
    recovered = fixtures.claim("alice", suite_base.claim_req(addrs["alice"]))
    assertions.expect_ok("recovery claim", recovered)
    reply = fixtures.claim_validate(recovered[1]["uri"], fresh, "bob",
                                    suite_base.validation(fresh))
    assertions.expect_ok("re-issued credential validates", reply)

    print("integration_core: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
