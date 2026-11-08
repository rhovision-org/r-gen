#!/usr/bin/env python3
"""Credential primitive: issue, prove, revoke, renew, attest, self-issue refusal."""

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
from terms import Raw


def main() -> int:
    if not suite_base.require("unit_credentials"):
        return 2
    addrs = suite_base.setup(("alice", "bob", "carol"))
    bob_cred = suite_base.issue(addrs, "bob", "Validator", "validator")
    carol_cred = suite_base.issue(addrs, "carol", "Approver", "approver")
    req = suite_base.requirement("Validator", "validator")

    reply = fixtures.call_uri(fixtures.comp("credential-factory"), "verify",
                              [bob_cred], deployer=False)
    assertions.expect_ok("credential registry verify", reply)
    reply = fixtures.call_uri(bob_cred, "get", [], deployer=False)
    assertions.expect_ok("credential get", reply)
    assertions.expect("credential active", reply[1].get("status"), "active")

    reply = fixtures.cred_prove(bob_cred, "bob", req)
    assertions.expect("prove returns proof and take", isinstance(reply, list), True)
    prove, take = reply
    assertions.expect_ok("bob prove", prove)
    corpus.assert_row("C1-prove-active", prove, primitive="credential")
    assertions.expect_ok("proof take", take)
    corpus.assert_row("PROOF-take-once", take)
    assertions.expect("proof subject", take[1].get("subject"), addrs["bob"])
    assertions.expect("proof credential uri", take[1].get("credentialUri"), bob_cred)

    replies = fixtures.cred_prove_twice(bob_cred, "bob", req)
    takes = [r for r in replies if isinstance(r, tuple) and r[0] is True]
    used = [r for r in replies if isinstance(r, tuple) and r[0] is False]
    assertions.expect("exactly one proof take", len(takes), 1)
    assertions.expect("second take refused", len(used), 1)

    reply = fixtures.cred_prove(bob_cred, "alice", req)
    assertions.expect_refusal("non-subject prove refused", reply, "not subject")
    corpus.assert_row("C1-prove-wrong-subject", reply)

    # `check` is advisory and caller-nominated: it compares the supplied address
    # with the stored subject. It is not a signature and no commit may use it
    # (RGA-027).
    reply = fixtures.cred_check_as(bob_cred, addrs["bob"], req)
    assertions.expect("advisory check true", reply[1], True)
    assertions.expect("advisory check names the credential", reply[2], bob_cred)
    reply = fixtures.cred_check_as(bob_cred, addrs["alice"], req)
    assertions.expect("advisory check wrong caller", reply[1], False)
    assertions.expect("advisory check wrong caller reason", reply[2], "not subject")
    reply = fixtures.cred_check_as(bob_cred, addrs["bob"],
                                   suite_base.requirement("Approver", "approver"))
    assertions.expect("advisory check scope", reply[1], False)
    assertions.expect("advisory check scope reason", reply[2], "scope")

    self_issue = fixtures.issue(actors.address("issuer"), "Validator", "structural",
                                "US-TX", "validator", 1)
    assertions.expect_refusal("self issue refused", self_issue, "self issue")

    non_issuer = fixtures.issue(addrs["alice"], "Validator", "structural", "US-TX",
                                "validator", 1, issuer="alice")
    assertions.expect("non-issuer authorized false", non_issuer[1], False)
    assertions.expect("non-issuer reason", non_issuer[2], "not issuer")

    reply = fixtures.call_uri(carol_cred, "attest", [Raw("*dId"), "attest-hash"],
                              key="bob")
    assertions.expect_ok("third-party attest", reply)
    corpus.assert_row("CRED-attest-thirdparty", reply)
    reply = fixtures.call_uri(carol_cred, "attest", [Raw("*dId"), "attest-2"], key="bob")
    assertions.expect_refusal("duplicate attest refused", reply, "already attested")
    reply = fixtures.call_uri(carol_cred, "attest", [Raw("*dId"), "attest-3"],
                              key="carol")
    assertions.expect_refusal("self attest refused", reply, "self attest")

    reply = fixtures.call_uri(carol_cred, "renew", [Raw("*dId"), 2000000, "renew-hash"],
                              key="issuer")
    assertions.expect_ok("issuer renew", reply)
    corpus.assert_row("CRED-renew", reply)
    reply = fixtures.call_uri(carol_cred, "renew", [Raw("*dId"), 1, "short"], key="bob")
    assertions.expect_refusal("subject cannot renew", reply, "not issuer")

    reply = fixtures.revoke_credential(bob_cred, "bob")
    assertions.expect_ok("revoke", reply)
    corpus.assert_row("CRED-revoke", reply)
    reply = fixtures.cred_prove(bob_cred, "bob", req)
    assertions.expect_refusal("revoked credential cannot prove", reply, "revoked")
    corpus.assert_row("C1-prove-revoked", reply)

    print("unit_credentials: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
