#!/usr/bin/env python3
"""Value proposition primitive: propose, validate, prove, dispute, withdraw."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import assertions
import corpus
import fixtures
import suite_base


def vp_req(addrs, proposer: str, selection: dict) -> dict:
    return {
        "subjectRef": {"type": "claim", "id": "pending", "uri": ""},
        "statementHash": f"vp-statement-{uuid.uuid4().hex[:6]}",
        "valueModelHash": "vp-model",
        "beneficiaries": [addrs[proposer]],
        "termsHash": "vp-terms",
        "selectionCriteria": selection,
        "deadlineHeight": 1000000,
    }


def main() -> int:
    if not suite_base.require("unit_value"):
        return 2
    addrs = suite_base.setup(("alice", "bob", "carol"))
    bob_cred = suite_base.issue(addrs, "bob", "Validator", "validator")
    selection = suite_base.requirement("Validator", "validator")

    vp = fixtures.vp_propose("alice", vp_req(addrs, "alice", selection))
    assertions.expect_ok("propose", vp)
    vp_uri = vp[1]["uri"]

    reply = fixtures.vp_validate(vp_uri, bob_cred, "bob",
                                 {"credentialUri": bob_cred, "notesHash": "notes"})
    assertions.expect_ok("validate", reply)
    reply = fixtures.vp_validate(vp_uri, bob_cred, "bob",
                                 {"credentialUri": bob_cred, "notesHash": "again"})
    assertions.expect_refusal("second validate refused", reply, "not proposed")
    corpus.assert_row("V1-validate-twice", reply)

    reply = fixtures.vp_prove_validated(vp_uri, "carol")
    assertions.expect("proveValidated returns proof and take", isinstance(reply, list), True)
    prove, take = reply
    assertions.expect_ok("proveValidated", prove)
    assertions.expect_ok("validated proof take", take)
    assertions.expect("validated proof caller", take[1].get("caller"), addrs["carol"])

    # Self-validation is refused.
    alice_cred = suite_base.issue(addrs, "alice", "Validator", "validator")
    vp2 = fixtures.vp_propose("alice", vp_req(addrs, "alice", selection))
    assertions.expect_ok("propose second", vp2)
    reply = fixtures.vp_validate(vp2[1]["uri"], alice_cred, "alice",
                                 {"credentialUri": alice_cred, "notesHash": "self"})
    assertions.expect_refusal("self validation refused", reply, "self validation")

    # A forged credential URI is refused by the append-only registry.
    forged = fixtures.vp_propose("alice", vp_req(addrs, "alice", selection))
    assertions.expect_ok("propose third", forged)
    reply = fixtures.vp_validate(forged[1]["uri"], fixtures.fake_uri(),
                                 "bob", {"credentialUri": "forged", "notesHash": "x"})
    assertions.expect_refusal("forged credential refused", reply, "forged credential")

    # Only the proposer withdraws.
    reply = fixtures.vp_withdraw(forged[1]["uri"], "bob")
    assertions.expect_refusal("non-proposer withdraw refused", reply, "not proposer")
    corpus.assert_row("VP-withdraw-nonproposer", reply)
    reply = fixtures.vp_withdraw(forged[1]["uri"], "alice")
    assertions.expect_ok("proposer withdraw", reply)
    reply = fixtures.vp_validate(forged[1]["uri"], bob_cred, "bob",
                                 {"credentialUri": bob_cred, "notesHash": "late"})
    assertions.expect_refusal("withdrawn cannot validate", reply, "not proposed")

    # Dispute and decision.
    case_req = {
        "kind": "dispute",
        "groundsHash": "grounds",
        "adjudicator": addrs["carol"],
        "adjudicatorCredentialUri": suite_base.issue(addrs, "carol", "Oracle", "oracle"),
        "deadlineHeight": 1000000,
    }
    opened = fixtures.vp_open_dispute(vp_uri, "alice", case_req)
    assertions.expect_ok("open dispute", opened)
    corpus.assert_row("VP-openDispute", opened)
    reply = fixtures.vp_prove_validated(vp_uri, "bob")
    assertions.expect_refusal("disputed cannot prove", reply, "not validated")
    corpus.assert_row("V2-prove-disputed", reply)

    decision = {"outcome": "uphold", "rationaleHash": "rationale"}
    assertions.expect_ok("decide dispute",
                         fixtures.oracle_decide(opened[1]["uri"], "carol", decision))
    assertions.expect_ok("execute dispute",
                         fixtures.oracle_execute(opened[1]["uri"]))
    reply = fixtures.read(vp_uri, "get")
    assertions.expect("VP upheld", reply[1].get("status"), "upheld")

    print("unit_value: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
