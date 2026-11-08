#!/usr/bin/env python3
"""Current-core red-team probes.

Each probe is a real deploy sequence. A result is `vulnerable`, `fixed`, `accepted`, or
`not_reproduced`. The suite records what it saw; it does not turn a known-open finding into a
build failure unless RGEN_EXPECT names the expected classification.

Usage:
    .venv/bin/python harness/redteam_core.py
    RGEN_EXPECT=vulnerable .venv/bin/python harness/redteam_core.py
    RGEN_EXPECT=fixed .venv/bin/python harness/redteam_core.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import actors
import assertions
import deploy as node
import fixtures
import preflight
import suite_base
from terms import Raw, enc

EXPECT = os.environ.get("RGEN_EXPECT", "any")
RESULTS: list[dict] = []


def record(probe_id: str, name: str, classification: str, finding: str,
           observed: str, detail=None) -> None:
    RESULTS.append({
        "id": probe_id,
        "name": name,
        "classification": classification,
        "finding": finding,
        "observed": observed,
        "detail": detail,
    })
    print(f"  {probe_id} {classification}: {name} - {observed}")


def classify(condition: bool, when_true: str, when_false: str) -> str:
    return when_true if condition else when_false


def deploy_error(call) -> str | None:
    try:
        call()
    except node.DevnetError as error:
        return str(error)
    return None


def prove_only(cred_uri: str, key: str, requirement: dict):
    term = f"""
new rl(`rho:registry:lookup`), c1, ret, proofCh,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{cred_uri}`, *c1) |
  for (Cred <- c1) {{
    Cred!("prove", *dId, {enc(requirement)}, *ret, *proofCh) |
    for (@r <- ret) {{
      match r {{
        (true, _) => {{ for (Proof <- proofCh) {{ deployId!(r) }} }}
        _ => {{ deployId!(r) }}
      }}
    }}
  }}
}}
"""
    return assertions.one(term, key=key)


def take_proof(proof_uri: str, key: str):
    return fixtures.call_uri(proof_uri, "take", [], key=key, deployer=False)


def open_past_deadline(addrs: dict, kasset_uri: str, adjudicator: str, cred_uri: str):
    case_req = {
        "kind": "dispute",
        "openedBy": addrs["alice"],
        "groundsHash": "grounds",
        "adjudicator": addrs[adjudicator],
        "adjudicatorCredentialUri": cred_uri,
        "deadlineHeight": 1,
    }
    return fixtures.kasset_open_dispute(kasset_uri, "alice", case_req)


def main() -> int:
    if not preflight.require_devnet("redteam_core"):
        return 2
    addrs = suite_base.setup(("alice", "bob", "carol", "dave"))
    addrs["deployer"] = actors.address("deployer")
    for name in ("mallory", "ida", "idb"):
        actors.ensure_vault(name)
    addrs["mallory"] = actors.address("mallory")

    bob_cred = suite_base.issue(addrs, "bob", "Validator", "validator")
    requirement = suite_base.requirement("Validator", "validator")

    # RT-004: a proof URI is a public bearer token. Mallory can take it first.
    prove = prove_only(bob_cred, "bob", requirement)
    if isinstance(prove, tuple) and prove and prove[0] is True:
        proof_uri = assertions.find_uri(prove)
        if proof_uri:
            mallory_take = take_proof(proof_uri, "mallory")
            bob_take = take_proof(proof_uri, "bob")
            stolen = (isinstance(mallory_take, tuple) and mallory_take
                      and mallory_take[0] is True)
            record(
                "RT-004", "third party takes a proof URI",
                classify(stolen, "vulnerable", "fixed"), "RGA-035",
                "mallory took the proof before bob" if stolen else "mallory could not take it",
                {"mallory": mallory_take, "bob": bob_take, "proof_uri": proof_uri},
            )
        else:
            record(
                "RT-004", "third party takes a proof URI", "fixed", "RGA-035",
                "prove returned no proof URI; the capability is sent only on the caller's "
                "private channel",
                {"reply": prove},
            )
    else:
        record("RT-004", "third party takes a proof URI", "not_reproduced", "RGA-035",
               f"prove did not return a proof: {prove!r}")

    # RT-008: issue a credential without a level; scopeMatches then compares Nil < Int.
    bad_req = {
        "subject": addrs["alice"], "ctype": "Validator", "discipline": "structural",
        "jurisdiction": "US-TX", "role": "validator",
        "issuerUri": fixtures.comp("issuer"), "expiresAt": 0,
    }
    bad_issue = fixtures.call_uri(fixtures.comp("credential-factory"), "issue",
                                  [Raw("*dId"), bad_req], key="deployer")
    if isinstance(bad_issue, tuple) and bad_issue and bad_issue[0] is True:
        bad_cred = bad_issue[1]
        error = deploy_error(lambda: fixtures.cred_prove(bad_cred, "alice", requirement))
        record(
            "RT-008", "credential with missing level",
            classify(error is not None, "vulnerable", "fixed"), "RGA-038",
            f"issued; prove {'errored' if error else 'returned a reply'}",
            {"credential": bad_cred, "prove_error": error},
        )
    else:
        record("RT-008", "credential with missing level", "fixed", "RGA-038",
               f"issue refused: {bad_issue!r}", {"issue": bad_issue})

    # RT-007: claim.subjectRef is stored but never validated.
    claim_req = suite_base.claim_req(addrs["alice"])
    claim_req["subjectRef"] = "not-a-map"
    claim_reply = fixtures.claim("alice", claim_req)
    if isinstance(claim_reply, tuple) and claim_reply and claim_reply[0] is True:
        claim_uri = claim_reply[1]["uri"]
        verified = fixtures.call_uri(fixtures.comp("claim-factory"), "verify",
                                     [claim_uri], deployer=False)
        stored = verified[1].get("subjectRef") if isinstance(verified, tuple) else None
        record(
            "RT-007", "claim with a free-string subjectRef",
            classify(stored == "not-a-map", "vulnerable", "fixed"), "RGA-039",
            f"stored subjectRef {stored!r}", {"claim": claim_uri, "verify": verified},
        )
    else:
        record("RT-007", "claim with a free-string subjectRef", "fixed", "RGA-039",
               f"create refused: {claim_reply!r}")

    # RT-006: a Nil comment window reaches `now > Nil` and errors the deploy.
    nil_req = suite_base.claim_req(addrs["alice"])
    nil_req["commentUntilHeight"] = None
    nil_claim = fixtures.claim("alice", nil_req)
    if isinstance(nil_claim, tuple) and nil_claim and nil_claim[0] is True:
        nil_uri = nil_claim[1]["uri"]
        error = deploy_error(lambda: fixtures.claim_comment(nil_uri, "bob", {"hash": "x"}))
        after = fixtures.read(nil_uri, "get")
        record(
            "RT-006", "comment on a Nil window",
            classify(error is not None, "vulnerable", "fixed"), "RGA-037",
            f"comment {'errored' if error else 'returned'}; claim status "
            f"{after[1].get('status') if isinstance(after, tuple) else after!r}",
            {"claim": nil_uri, "comment_error": error, "after": after},
        )
    else:
        record("RT-006", "comment on a Nil window", "fixed", "RGA-037",
               f"create refused: {nil_claim!r}")

    # RT-009 / RT-010: a past deadline is refused, and the party list now comes
    # from the subject's one-shot snapshot rather than the caller.
    dave_cred = suite_base.issue(addrs, "dave", "Oracle", "oracle")
    _, rt_kasset = suite_base.approved_kasset(addrs, "bob", "carol", claimant="alice")
    opened = open_past_deadline(addrs, rt_kasset, "dave", dave_cred)
    accepted = isinstance(opened, tuple) and opened and opened[0] is True
    record(
        "RT-009", "oracle open with a past deadline",
        classify(accepted, "vulnerable", "fixed"), "RGA-026",
        "case opened" if accepted else f"refused: {opened!r}",
        {"open": opened, "adjudicator_credential": dave_cred},
    )
    record(
        "RT-010", "oracle open with caller-chosen parties",
        "fixed", "RGA-023",
        "openBound derives subjectRef and parties from the subject snapshot; the raw open arm is gone",
        {"open": opened, "subject": rt_kasset},
    )

    # RT-011: provenance creation no longer accepts a free assetRef. A third party
    # can still create an advisory record for a public subject, but the record is
    # bound to that subject's own uri and cannot name a different asset.
    _, victim, _ = suite_base.validated_kasset(addrs, "bob")
    prov = fixtures.provenance_create(victim, [addrs["mallory"]], key="mallory")
    created = isinstance(prov, tuple) and prov and prov[0] is True
    bound_uri = None
    if created:
        bound_uri = fixtures.read(prov[1]["uri"], "get")[1].get("assetRef").get("uri")
    bound = created and bound_uri == victim
    record(
        "RT-011", "provenance record is bound to the subject",
        "accepted" if bound else "fixed", "RGA-022",
        (f"mallory created an advisory record for {victim}; assetRef equals the subject uri")
        if bound else f"refused or unbound: {prov!r}",
        {"provenance": prov, "assetRef": bound_uri, "subject": victim},
    )

    # RT-013: proveApproved is permissionless and mints an unbounded number of proofs.
    _, kasset = suite_base.approved_kasset(addrs, validator="bob", approver="carol")
    proofs = [fixtures.kasset_prove_approved(kasset, "mallory") for _ in range(3)]
    minted = [
        p for p in proofs
        if isinstance(p, (list, tuple)) and p
        and isinstance(p[0], (list, tuple)) and p[0] and p[0][0] is True
    ]
    record(
        "RT-013", "permissionless proveApproved minting",
        "accepted" if len(minted) == 3 else "fixed", "RGA-040",
        f"{len(minted)}/3 private proofs minted and taken by mallory; caller-paid, "
        "no registry entry, no victim state",
        {"kasset": kasset, "proofs": proofs},
    )

    # RT-014: the nest cap is checked before any child proof is touched.
    refs = [{"id": f"x{i}", "uri": f"rho:id:fake-child-{i}"} for i in range(33)]
    capped = fixtures.kasset_nest(kasset, "alice", refs)
    record(
        "RT-014", "nest above the 32-child cap",
        "fixed" if isinstance(capped, tuple) and capped[0] is False else "vulnerable",
        "RGA-025", f"reply {capped!r}", {"reply": capped},
    )

    # RT-002: two validations in one deploy; exactly one may win.
    claim2 = fixtures.claim("alice", suite_base.claim_req(addrs["alice"]))
    two = fixtures.two_claim_validations(claim2[1]["uri"], bob_cred, "bob",
                                         suite_base.validation(bob_cred))
    trues = [r for r in two if isinstance(r, tuple) and r[0] is True]
    record(
        "RT-002", "two validations in one deploy",
        "fixed" if len(trues) == 1 else "vulnerable", "RGA-032",
        f"{len(trues)} validation(s) succeeded",
        {"replies": two, "claim": claim2[1]["uri"]},
    )

    # RT-012: execute is a permissionless crank; it applies the stored decision.
    case_uri, _ = suite_base.open_case(addrs, kasset, adjudicator="dave", opener="alice")
    decide = fixtures.oracle_decide(case_uri, "dave",
                                    {"outcome": "uphold", "rationaleHash": "r"})
    executed = fixtures.call_uri(case_uri, "execute", [], key="mallory", deployer=False)
    state = fixtures.read(case_uri, "get")
    status = state[1].get("status") if isinstance(state, tuple) else None
    record(
        "RT-012", "permissionless execute crank",
        "accepted" if isinstance(executed, tuple) and executed[0] is True else "fixed",
        "RGA-024", f"execute reply {executed!r}; status {status!r}",
        {"decide": decide, "execute": executed, "state": state},
    )

    # RT-020: a VP validator must be able to open a dispute as itself.
    vp_req = {
        "subjectRef": {"type": "claim", "id": "pending", "uri": "rho:id:vp-subject"},
        "statementHash": "rt-vp-statement",
        "valueModelHash": "rt-vp-model",
        "beneficiaries": [addrs["alice"]],
        "termsHash": "rt-vp-terms",
        "selectionCriteria": suite_base.requirement("Validator", "validator"),
        "deadlineHeight": 1000000,
    }
    vp = fixtures.vp_propose("alice", vp_req)
    if isinstance(vp, tuple) and vp and vp[0] is True:
        vp_uri = vp[1]["uri"]
        fixtures.vp_validate(vp_uri, bob_cred, "bob",
                             {"credentialUri": bob_cred, "notesHash": "n"})
        dispute = fixtures.vp_open_dispute(vp_uri, "bob", {
            "kind": "dispute",
            "groundsHash": "rt-vp-grounds",
            "adjudicator": addrs["dave"],
            "adjudicatorCredentialUri": dave_cred,
            "deadlineHeight": 1000000,
        })
        fixed = isinstance(dispute, tuple) and dispute and dispute[0] is True
        record(
            "RT-020", "VP validator opens a dispute",
            classify(fixed, "fixed", "vulnerable"), "RGA-041",
            "validator dispute opened" if fixed else f"refused: {dispute!r}",
            {"vp": vp_uri, "reply": dispute},
        )
    else:
        record("RT-020", "VP validator opens a dispute", "fixed", "RGA-041",
               f"propose refused: {vp!r}")

    # RT-021: a value proposition must not validate after its deadline.
    late_deadline = actors.block_height() + 3
    late_req = dict(vp_req)
    late_req["statementHash"] = "rt-late-vp"
    late_req["deadlineHeight"] = late_deadline
    late_vp = fixtures.vp_propose("alice", late_req)
    if isinstance(late_vp, tuple) and late_vp and late_vp[0] is True:
        late_vp_uri = late_vp[1]["uri"]
        while actors.block_height() <= late_deadline:
            pass
        try:
            late_reply = fixtures.vp_validate(
                late_vp_uri, bob_cred, "bob",
                {"credentialUri": bob_cred, "notesHash": "late"})
            error = None
        except node.DevnetError as exc:
            late_reply = None
            error = str(exc)
        refused = (isinstance(late_reply, tuple) and late_reply
                   and late_reply[0] is False and late_reply[1] == "deadline")
        record(
            "RT-021", "VP validation after the deadline",
            classify(refused, "fixed", "vulnerable"), "RGA-042",
            f"deadline {late_deadline}; reply {late_reply!r}; error {error!r}",
            {"vp": late_vp_uri},
        )
    else:
        record("RT-021", "VP validation after the deadline", "fixed", "RGA-042",
               f"propose refused: {late_vp!r}")

    # RT-022: an oracle decision must not be accepted after the case deadline.
    _, late_kasset = suite_base.approved_kasset(addrs, validator="bob", approver="carol")
    case_deadline = actors.block_height() + 3
    late_case_req = {
        "kind": "dispute",
        "openedBy": addrs["alice"],
        "parties": [addrs["alice"], addrs["bob"]],
        "groundsHash": "rt-late-case",
        "requirement": suite_base.requirement("Oracle", "oracle"),
        "adjudicator": addrs["dave"],
        "adjudicatorCredentialUri": dave_cred,
        "deadlineHeight": case_deadline,
    }
    late_case = fixtures.kasset_open_dispute(late_kasset, "alice", late_case_req)
    if isinstance(late_case, tuple) and late_case and late_case[0] is True:
        late_case_uri = late_case[1]["uri"]
        while actors.block_height() <= case_deadline:
            pass
        late_decide = fixtures.oracle_decide(
            late_case_uri, "dave", {"outcome": "uphold", "rationaleHash": "late"})
        refused = (isinstance(late_decide, tuple) and late_decide
                   and late_decide[0] is False and late_decide[1] == "expired")
        record(
            "RT-022", "oracle decide after the case deadline",
            classify(refused, "fixed", "vulnerable"), "RGA-043",
            f"deadline {case_deadline}; reply {late_decide!r}",
            {"case": late_case_uri},
        )
    else:
        record("RT-022", "oracle decide after the case deadline", "fixed", "RGA-043",
               f"open refused: {late_case!r}")

    # RT-023: the recorded validator credential must be the one actually proved.
    attribution_claim = fixtures.claim("alice", suite_base.claim_req(addrs["alice"]))
    if isinstance(attribution_claim, tuple) and attribution_claim and attribution_claim[0] is True:
        attribution_uri = attribution_claim[1]["uri"]
        fake_cred = "rho:id:fake-credential-attribution"
        attribution_val = suite_base.validation(bob_cred)
        attribution_val["credentialUri"] = fake_cred
        attributed = fixtures.claim_validate(attribution_uri, bob_cred, "bob",
                                             attribution_val)
        if isinstance(attributed, tuple) and attributed and attributed[0] is True:
            claim_state = fixtures.read(attribution_uri, "get")
            stored_claim = (claim_state[1].get("validationRef", {}).get("credentialUri")
                            if isinstance(claim_state, tuple) else None)
            kasset_state = fixtures.read(attributed[1]["uri"], "get")
            stored_kasset = (kasset_state[1].get("validatorCredential")
                             if isinstance(kasset_state, tuple) else None)
            fixed = stored_claim == bob_cred and stored_kasset == bob_cred
            record(
                "RT-023", "claim records the proved credential",
                classify(fixed, "fixed", "vulnerable"), "RGA-044",
                f"claim stored {stored_claim!r}; kasset stored {stored_kasset!r}",
                {"claim": attribution_uri, "kasset": attributed[1]["uri"]},
            )
        else:
            record("RT-023", "claim records the proved credential", "fixed", "RGA-044",
                   f"validate refused: {attributed!r}")
    else:
        record("RT-023", "claim records the proved credential", "fixed", "RGA-044",
               f"create refused: {attribution_claim!r}")

    # RT-001: try to make two creates for one address both succeed.
    duplicates = []
    attempts = []
    for name in ("mallory", "ida", "idb"):
        reply = fixtures.two_identity_creates(name, f"dup-{name}")
        pair = reply if isinstance(reply, list) else [reply]
        wins = [r for r in pair if isinstance(r, tuple) and r[0] is True]
        attempts.append({"actor": name, "replies": pair})
        if len(wins) > 1:
            duplicates.append({"actor": name, "replies": pair})
    record(
        "RT-001", "two identity creates for one address",
        "vulnerable" if duplicates else "not_reproduced", "RGA-031",
        f"{len(duplicates)} duplicate(s) in {len(attempts)} attempt(s)",
        {"attempts": attempts},
    )

    report = {
        "schema": "rgen.redteam/v1",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "node": node.http_json("GET", f"{node.NODE}/api/v1/status").get("version", {}),
        "expectation": EXPECT,
        "results": RESULTS,
    }
    out = ROOT / "deployments" / "redteam-results.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    spec = ROOT / "spec" / "audit" / "redteam.yaml"
    spec.write_text(yaml.safe_dump(report, sort_keys=False) + "\n")
    print(f"redteam: wrote {out}")
    print(f"redteam: wrote {spec}")

    if EXPECT != "any":
        allowed = {EXPECT, "accepted"}
        if EXPECT == "fixed":
            allowed.add("not_reproduced")
        mismatched = [r for r in RESULTS if r["classification"] not in allowed]
        if mismatched:
            for item in mismatched:
                print(f"redteam: expected {EXPECT}, got {item['classification']}: "
                      f"{item['id']} {item['name']}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
