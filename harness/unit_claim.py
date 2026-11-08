#!/usr/bin/env python3
"""Claim primitive: comment, withdraw, expire, validate once, exactly one K-Asset."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import actors
import assertions
import corpus
import fixtures
import suite_base


def main() -> int:
    if not suite_base.require("unit_claim"):
        return 2
    addrs = suite_base.setup(("alice", "bob", "carol"))
    actors.ensure_vault("frank")  # funded but deliberately has no identity
    bob_cred = suite_base.issue(addrs, "bob", "Validator", "validator")

    req = suite_base.claim_req(addrs["alice"])
    reply = fixtures.claim("alice", req)
    assertions.expect_ok("create claim", reply)
    claim_uri = reply[1]["uri"]
    assertions.expect("claim open", fixtures.read(claim_uri, "get")[1].get("status"), "open")
    reply = fixtures.claim_resume(claim_uri, "alice")
    assertions.expect_refusal("resume open claim refused", reply, "not resumable")

    # Comment no longer requires directory registration; frank has no identity.
    reply = fixtures.claim_comment(claim_uri, "frank", {"hash": "frank-comment"})
    assertions.expect_ok("unregistered actor comments", reply)
    corpus.assert_row("CLAIM-comment", reply)
    reply = fixtures.read(claim_uri, "comments")
    assertions.expect("comment stored", len(reply[1]), 1)

    reply = fixtures.claim_expire(claim_uri)
    assertions.expect_refusal("early expire refused", reply, "not expired")
    corpus.assert_row("CLAIM-expire-early", reply)
    reply = fixtures.claim_withdraw(claim_uri, "bob")
    assertions.expect_refusal("non-claimant withdraw refused", reply, "not claimant")
    corpus.assert_row("CLAIM-withdraw-nonclaimant", reply)
    reply = fixtures.claim_withdraw(claim_uri, "alice")
    assertions.expect_ok("claimant withdraw", reply)
    reply = fixtures.claim_validate(claim_uri, bob_cred, "bob",
                                    suite_base.validation(bob_cred))
    assertions.expect_refusal("withdrawn cannot validate", reply, "not open")

    # Validate once, exactly one K-Asset.
    claim2 = fixtures.claim("alice", suite_base.claim_req(addrs["alice"]))
    assertions.expect_ok("second claim", claim2)
    reply = fixtures.call_uri(fixtures.comp("claim-factory"), "verify",
                              [claim2[1]["uri"]], deployer=False)
    assertions.expect_ok("claim verify", reply)
    corpus.assert_row("CLAIM-verify", reply)
    claim2_uri = claim2[1]["uri"]
    reply = fixtures.claim_validate(claim2_uri, bob_cred, "bob",
                                    suite_base.validation(bob_cred))
    assertions.expect_ok("validate claim", reply)
    kasset_uri = reply[1]["uri"]
    reply = fixtures.read(claim2_uri, "get")
    assertions.expect("claim validated", reply[1].get("status"), "validated")
    assertions.expect("one kasset ref", reply[1].get("kassetRef").get("uri"), kasset_uri)
    reply = fixtures.claim_resume(claim2_uri, "alice")
    assertions.expect_refusal("resume final claim refused", reply, "not resumable")
    assertions.expect("resume cannot change kasset ref",
                      fixtures.read(claim2_uri, "get")[1].get("kassetRef").get("uri"),
                      kasset_uri)
    reply = fixtures.claim_validate(claim2_uri, bob_cred, "bob",
                                    suite_base.validation(bob_cred, "invalid"))
    assertions.expect_refusal("second validate refused", reply, "not open")
    corpus.assert_row("C1-claim-validate-once", reply)

    # Self-validation.
    alice_cred = suite_base.issue(addrs, "alice", "Validator", "validator")
    claim3 = fixtures.claim("alice", suite_base.claim_req(addrs["alice"]))
    assertions.expect_ok("third claim", claim3)
    reply = fixtures.claim_validate(claim3[1]["uri"], alice_cred, "alice",
                                    suite_base.validation(alice_cred))
    assertions.expect_refusal("self validation refused", reply, "self validation")

    # Forged credential.
    claim4 = fixtures.claim("alice", suite_base.claim_req(addrs["alice"]))
    assertions.expect_ok("fourth claim", claim4)
    reply = fixtures.claim_validate(claim4[1]["uri"], fixtures.fake_uri(), "bob",
                                    suite_base.validation("forged"))
    assertions.expect_refusal("forged credential refused", reply, "forged credential")

    # Late validation marks the claim expired. Creation now requires a future deadline
    # (RR-07), so create just ahead of the tip and let a deploy pass it.
    deadline = actors.block_height() + 10
    late = suite_base.claim_req(addrs["alice"])
    late["deadlineHeight"] = deadline
    late["commentUntilHeight"] = deadline
    claim5 = fixtures.claim("alice", late)
    assertions.expect_ok("late claim", claim5)
    for _ in range(20):
        if actors.block_height() > deadline:
            break
    reply = fixtures.claim_validate(claim5[1]["uri"], bob_cred, "bob",
                                    suite_base.validation(bob_cred))
    assertions.expect_refusal("late validation refused", reply, "expired")
    assertions.expect("late claim expired",
                      fixtures.read(claim5[1]["uri"], "get")[1].get("status"), "expired")

    # A claim created with a past deadline is refused by the create guard (RR-07).
    past = suite_base.claim_req(addrs["alice"])
    past["deadlineHeight"] = 0
    assertions.expect_refusal("past deadline refused", fixtures.claim("alice", past), "fields")

    # A claim cannot bind a value proposition the genuine factory did not issue
    # (RGA-046). The reference is checked at creation; validation still re-checks
    # that the VP is validated at approval.
    forged_uri = fixtures.fake_uri()
    forged_vp = suite_base.claim_req(addrs["alice"])
    forged_vp["valuePropositionRef"] = {"id": forged_uri, "uri": forged_uri}
    assertions.expect_refusal("forged value proposition refused",
                              fixtures.claim("alice", forged_vp), "value proposition")

    # Comment window closes.
    closed = suite_base.claim_req(addrs["alice"])
    closed["commentUntilHeight"] = 0
    claim6 = fixtures.claim("alice", closed)
    assertions.expect_ok("closed-window claim", claim6)
    reply = fixtures.claim_comment(claim6[1]["uri"], "bob", {"hash": "late"})
    assertions.expect_refusal("comment window closed", reply, "comment closed")

    print("unit_claim: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
