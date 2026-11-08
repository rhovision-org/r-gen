#!/usr/bin/env python3
"""Oracle primitive: stored adjudicator credential, decide once, subject-bound execute."""

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
    if not suite_base.require("unit_oracle"):
        return 2
    addrs = suite_base.setup(("alice", "bob", "carol", "dave"))
    _, kasset_uri = suite_base.approved_kasset(addrs, "bob", "carol")

    # A past deadline is refused at open (RGA-026); the K-Asset stays approved,
    # so the valid dispute below still opens.
    past_cred = suite_base.issue(addrs, "dave", "Oracle", "oracle")
    past = {
        "kind": "dispute",
        "groundsHash": "grounds",
        "adjudicator": addrs["dave"],
        "adjudicatorCredentialUri": past_cred,
        "deadlineHeight": 1,
    }
    reply = fixtures.kasset_open_dispute(kasset_uri, "alice", past)
    assertions.expect_refusal("past oracle deadline refused", reply, "case fields")

    case_uri, adjudicator_cred = suite_base.open_case(addrs, kasset_uri, "dave")

    reply = fixtures.read(case_uri, "get")
    assertions.expect("case open", reply[1].get("status"), "open")
    assertions.expect("case stores credential",
                      reply[1].get("adjudicatorCredentialUri"), adjudicator_cred)

    reply = fixtures.call_uri(case_uri, "expire", [], deployer=False)
    assertions.expect_refusal("early expire refused", reply, "not expired")
    corpus.assert_row("ORACLE-expire-early", reply)

    decision = {"outcome": "uphold", "rationaleHash": "rationale"}
    reply = fixtures.oracle_decide(case_uri, "bob", decision)
    assertions.expect_refusal("non-adjudicator decide refused", reply, "not adjudicator")

    reply = fixtures.oracle_decide(case_uri, "dave", {"outcome": "bogus"})
    assertions.expect_refusal("bad outcome refused", reply, "outcome")

    reply = fixtures.oracle_decide(case_uri, "dave", decision)
    assertions.expect_ok("adjudicator decide", reply)
    corpus.assert_row("ORACLE-decide", reply)
    reply = fixtures.oracle_decide(case_uri, "dave", decision)
    assertions.expect_refusal("second decide refused", reply, "not open")

    reply = fixtures.oracle_execute(case_uri)
    assertions.expect_ok("execute", reply)
    corpus.assert_row("KASSET-applyDecision", reply)
    reply = fixtures.oracle_execute(case_uri)
    assertions.expect("second execute is already executed", reply[1], "already executed")
    corpus.assert_row("O1-execute-twice", reply)
    assertions.expect("K-Asset upheld", fixtures.read(kasset_uri, "get")[1].get("status"),
                      "upheld")

    reply = fixtures.call_uri(case_uri, "close", [], deployer=False)
    assertions.expect_ok("close executed case", reply)
    assertions.expect("case closed", fixtures.read(case_uri, "get")[1].get("status"),
                      "closed")

    # A case with a forged adjudicator credential is refused at open.
    _, second = suite_base.approved_kasset(addrs, "bob", "carol")
    forged = {
        "kind": "dispute",
        "groundsHash": "grounds",
        "adjudicator": addrs["dave"],
        "adjudicatorCredentialUri": fixtures.fake_uri(),
        "deadlineHeight": 1000000,
    }
    reply = fixtures.kasset_open_dispute(second, "alice", forged)
    assertions.expect_refusal("forged adjudicator credential refused", reply,
                              "adjudicator credential")

    # A credential that expires before the case deadline is refused at open.
    expired_cred = suite_base.issue(addrs, "dave", "Oracle", "oracle", expires_at=1)
    expired_req = {
        "kind": "dispute",
        "groundsHash": "grounds",
        "adjudicator": addrs["dave"],
        "adjudicatorCredentialUri": expired_cred,
        "deadlineHeight": 1000000,
    }
    reply = fixtures.kasset_open_dispute(second, "alice", expired_req)
    assertions.expect_refusal("expired adjudicator credential refused", reply,
                              "adjudicator credential")

    # An open case cannot close.
    third_case, _ = suite_base.open_case(addrs, second, "dave")
    reply = fixtures.call_uri(third_case, "close", [], deployer=False)
    assertions.expect_refusal("open case cannot close", reply, "not finished")
    corpus.assert_row("O2-close-open", reply)

    # Evidence is restricted to parties and the adjudicator.
    reply = fixtures.call_uri(third_case, "evidence", [Raw("*dId"), {"hash": "ev"}],
                              key="dave")
    assertions.expect_ok("adjudicator evidence", reply)
    corpus.assert_row("ORACLE-evidence-party", reply)
    reply = fixtures.call_uri(third_case, "evidence", [Raw("*dId"), {"hash": "ev"}],
                              key="deployer")
    assertions.expect_refusal("non-party evidence refused", reply, "not a party")

    # A decided case has a terminal abandon path; a non-adjudicator cannot use it
    # (RGA-071). The execution attempt count starts at 1 even when execute never ran.
    reply = fixtures.oracle_decide(third_case, "dave", decision)
    assertions.expect_ok("decide before abandon", reply)
    reply = fixtures.call_uri(third_case, "abandon", [Raw("*dId")], key="bob")
    assertions.expect_refusal("non-adjudicator abandon refused", reply, "not adjudicator")
    reply = fixtures.call_uri(third_case, "abandon", [Raw("*dId")], key="dave")
    assertions.expect_ok("adjudicator abandon", reply)
    state = fixtures.read(third_case, "get")[1]
    assertions.expect("abandon closes the case", state.get("status"), "closed")
    assertions.expect("abandon records the terminal status",
                      state.get("execution").get("status"), "abandoned")
    reply = fixtures.oracle_execute(third_case)
    assertions.expect_refusal("abandoned case cannot execute", reply, "not decided")

    # An expired dispute restores the subject's prior status (RGA-064).
    _, expiry_kasset = suite_base.approved_kasset(addrs, "bob", "carol")
    expiry_cred = suite_base.issue(addrs, "dave", "Oracle", "oracle")
    deadline = actors.block_height() + 3
    expiry_req = {
        "kind": "dispute",
        "groundsHash": "grounds",
        "adjudicator": addrs["dave"],
        "adjudicatorCredentialUri": expiry_cred,
        "deadlineHeight": deadline,
    }
    reply = fixtures.kasset_open_dispute(expiry_kasset, "alice", expiry_req)
    assertions.expect_ok("short-deadline dispute opened", reply)
    expiry_case = reply[1]["uri"]
    for _ in range(20):
        if actors.block_height() > deadline:
            break
    reply = fixtures.call_uri(expiry_case, "expire", [], deployer=False)
    assertions.expect_ok("expire dispute", reply)
    assertions.expect("expired dispute restores K-Asset",
                      fixtures.read(expiry_kasset, "get")[1].get("status"), "approved")

    print("unit_oracle: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
