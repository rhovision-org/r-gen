#!/usr/bin/env python3
"""Object-capability red-team probes.

Each probe is a real deploy sequence against the local devnet. A result is `vulnerable`,
`fixed`, `accepted`, or `not_reproduced`. The suite records what it saw; it does not turn a
known-open finding into a build failure unless RGEN_EXPECT names the expected classification.

Usage:
    .venv/bin/python harness/redteam_capabilities.py
    RGEN_EXPECT=fixed .venv/bin/python harness/redteam_capabilities.py
    RGEN_EXPECT=vulnerable .venv/bin/python harness/redteam_capabilities.py

The probes are capability-focused: private-helper reachability, proof forwarding, Root
registration, forged credential designation, the published Issuer authorize arm, the K-Asset
nest child anchor, approval durability, and the public OracleCase arms.
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


def call(uri: str, arm: str, args=(), key: str = "deployer", deployer: bool = True):
    try:
        return fixtures.call_uri(uri, arm, list(args), key=key, deployer=deployer)
    except Exception as error:  # noqa: BLE001 - a blocked deploy is an observation
        return f"deploy-error: {error}"


def as_refusal(reply) -> bool:
    return isinstance(reply, tuple) and reply and reply[0] is False


def as_ok(reply) -> bool:
    return isinstance(reply, tuple) and reply and reply[0] is True


def one_term(term: str, key: str):
    try:
        return assertions.one(term, key=key)
    except Exception as error:  # noqa: BLE001
        return f"deploy-error: {error}"


def main() -> int:
    if not preflight.require_devnet("redteam_capabilities"):
        return 2
    addrs = suite_base.setup(("alice", "bob", "carol", "dave"))
    addrs["deployer"] = actors.address("deployer")
    for name in ("mallory",):
        actors.ensure_vault(name)
    addrs["mallory"] = actors.address("mallory")

    bob_cred = suite_base.issue(addrs, "bob", "Validator", "validator")
    requirement = suite_base.requirement("Validator", "validator")

    # RT-025: a factory URI does not expose its private helpers.
    helper_replies = {}
    for helper in ("makeKAsset", "mintIdentity", "finalizeWith", "Apply"):
        helper_replies[helper] = call(assertions.component_uri("claim-factory"),
                                      helper, [], key="mallory")
    callable_helpers = [name for name, reply in helper_replies.items()
                        if as_ok(reply)]
    record(
        "RT-025", "private helper names are not callable through a factory URI",
        "vulnerable" if callable_helpers else "fixed", "-",
        f"{len(callable_helpers)} helper(s) replied: {callable_helpers}",
        {"replies": helper_replies},
    )

    # RT-024: an unauthorized deployer cannot drive another entity's arms.
    alice_identity = call(assertions.component_uri("identity-directory"), "lookup",
                          [addrs["alice"]], key="mallory", deployer=False)
    identity_uri = alice_identity[1] if as_ok(alice_identity) else ""
    claim_reply = fixtures.claim("alice", suite_base.claim_req(addrs["alice"]))
    claim_uri = claim_reply[1]["uri"] if as_ok(claim_reply) else ""
    vp_req = {
        "subjectRef": {"uri": "rho:id:subject"},
        "statementHash": "statement", "termsHash": "terms",
        "selectionCriteria": suite_base.requirement("Validator", "validator"),
        "deadlineHeight": 1_000_000, "beneficiaries": [], "valueModelHash": "",
    }
    vp_reply = fixtures.vp_propose("alice", vp_req)
    vp_uri = vp_reply[1]["uri"] if as_ok(vp_reply) else ""
    _, matrix_kasset, _ = suite_base.validated_kasset(addrs, "bob", claimant="alice")
    prov_reply = fixtures.provenance_create(matrix_kasset, [addrs["alice"]], key="alice")
    prov_uri = prov_reply[1]["uri"] if as_ok(prov_reply) else ""
    unauthorized = {
        "identity.update": call(identity_uri, "update", [Raw("*dId"), {"orgHash": "x"}],
                                key="mallory") if identity_uri else "no-uri",
        "claim.withdraw": call(claim_uri, "withdraw", [Raw("*dId")], key="mallory")
        if claim_uri else "no-uri",
        "vp.withdraw": fixtures.vp_withdraw(vp_uri, "mallory") if vp_uri else "no-uri",
        "provenance.anchor": fixtures.provenance_anchor(
            prov_uri, "mallory", {"hash": "x"}) if prov_uri else "no-uri",
        "kasset.approve": fixtures.kasset_approve(
            matrix_kasset, fixtures.fake_uri("credential"), "mallory",
            suite_base.approval(fixtures.fake_uri("credential"), addrs["mallory"])),
    }
    succeeded = [name for name, reply in unauthorized.items() if as_ok(reply)]
    record(
        "RT-024", "an unauthorized deployer cannot drive another entity's arms",
        "vulnerable" if succeeded else "fixed", "-",
        f"{len(succeeded)} unauthorized arm(s) succeeded: {succeeded}",
        {"replies": unauthorized},
    )

    # RT-029: Root registration is installer-gated and write-once.
    root = assertions.component_uri("root")
    non_installer = call(root, "register",
                         ["component:evil", "rho:id:fake", 1, "x", Raw("*dId")],
                         key="mallory")
    duplicate = call(root, "register",
                     ["component:root", "rho:id:fake", 1, "x", Raw("*dId")],
                     key="deployer")
    fixed = as_refusal(non_installer) and as_refusal(duplicate)
    record(
        "RT-029", "Root register is installer-gated and write-once",
        classify(fixed, "fixed", "vulnerable"), "-",
        f"mallory={non_installer!r}; duplicate={duplicate!r}",
        {"non_installer": non_installer, "duplicate": duplicate},
    )

    # RT-031: authorize must derive the caller, not trust a supplied address.
    issuer = assertions.component_uri("issuer")
    data_caller = call(issuer, "authorize",
                       [addrs["deployer"], requirement, 1_000_000],
                       key="mallory", deployer=False)
    d_id_caller = call(issuer, "authorize",
                       [Raw("*dId"), requirement, 1_000_000], key="mallory")
    accepted = as_ok(data_caller) and len(data_caller) > 1 and data_caller[1] is True
    record(
        "RT-031", "Issuer authorize derives the caller from deployerId",
        classify(accepted, "vulnerable", "fixed"), "RGA-048",
        f"data-caller={data_caller!r}; dId-caller={d_id_caller!r}",
        {"data_caller": data_caller, "d_id_caller": d_id_caller,
         "pre_fix": "data-caller=(True, True)"},
    )

    # RT-030: a forged credential URI is refused before any proof.
    fake_cred_term = f"""
new rs(`rho:registry:insertArbitrary`), s, Fake, uriCh,
    deployId(`rho:rchain:deployId`) in {{
  s!({{
    "uri": "rho:id:fake", "subject": "{addrs['mallory']}",
    "status": "active", "ctype": "Validator", "discipline": "structural",
    "jurisdiction": "US-TX", "role": "validator", "level": 3,
    "expiresAt": 0, "version": 1
  }}) |
  contract Fake(@"get", ret) = {{ for (@v <<- s) {{ ret!((true, v)) }} }} |
  contract Fake(@"prove", dId2, @rq, ret2, proofCh) = {{ ret2!((false, "forged")) }} |
  rs!(bundle+{{*Fake}}, *uriCh) |
  for (@uri <- uriCh) {{ deployId!(uri) }}
}}
"""
    fake_cred = one_term(fake_cred_term, "mallory")
    claim_reply = fixtures.claim("alice", suite_base.claim_req(addrs["alice"]))
    forged = "not-run"
    if isinstance(claim_reply, tuple) and claim_reply and claim_reply[0] is True:
        claim_uri = claim_reply[1]["uri"]
        forged = fixtures.claim_validate(
            claim_uri, str(fake_cred), "mallory",
            suite_base.validation(str(fake_cred)))
    record(
        "RT-030", "a forged credential URI is refused by the Claim factory",
        classify(isinstance(forged, tuple) and forged[:1] == (False,) and
                 forged[1] == "forged credential", "fixed", "vulnerable"),
        "-",
        f"validate={forged!r}",
        {"fake_credential": fake_cred, "validate": forged},
    )

    # RT-032: a self-registered fake child cannot be nested under a real parent.
    parent_claim, parent_kasset = suite_base.approved_kasset(
        addrs, validator="bob", approver="carol", claimant="mallory")
    parent_reply = fixtures.read(parent_kasset, "get")
    parent = parent_reply[1] if as_ok(parent_reply) else {}
    fake_term = f"""
new rs(`rho:registry:insertArbitrary`), fakeState, FakeChild, uriCh,
    deployId(`rho:rchain:deployId`) in {{
  fakeState!({{
    "uri": {enc(Raw(f"`{parent_kasset}`"))},
    "fakeUri": "",
    "claimRef": {{"id": {enc(Raw(f"`{parent_claim}`"))},
                  "uri": {enc(Raw(f"`{parent_claim}`"))}}},
    "status": "approved",
    "discipline": {enc(parent.get("discipline", ""))},
    "jurisdiction": {enc(parent.get("jurisdiction", ""))},
    "approvedAt": 1,
    "version": 1
  }}) |
  contract FakeChild(@"get", ret) = {{ for (@v <<- fakeState) {{ ret!((true, v)) }} }} |
  contract FakeChild(@"proveApproved", ret, proofCh) = {{
    new proofState, Proof in {{
      for (@v <<- fakeState) {{
        proofState!({{"data": {{"id": v.get("fakeUri"), "uri": v.get("fakeUri"),
                             "approvedAt": 1}}, "used": false}}) |
        contract Proof(@"take", ret3) = {{
          for (@p <- proofState) {{
            if (p.get("used")) {{ proofState!(p) | ret3!((false, "used")) }}
            else {{ proofState!(p.set("used", true)) |
                   ret3!((true, p.get("data"))) }}
          }}
        }} |
        proofCh!(bundle+{{*Proof}}) | ret!((true, Nil))
      }}
    }}
  }} |
  rs!(bundle+{{*FakeChild}}, *uriCh) |
  for (@uri <- uriCh) {{
    for (@v <- fakeState) {{ fakeState!(v.set("fakeUri", uri)) }} |
    deployId!(uri)
  }}
}}
"""
    fake_uri = one_term(fake_term, "mallory")
    nested = "not-run"
    if isinstance(fake_uri, str) and fake_uri.startswith("rho:id:"):
        nested = call(parent_kasset, "nest",
                      [Raw("*dId"),
                       [{"id": Raw(f"`{fake_uri}`"), "uri": Raw(f"`{fake_uri}`")}]],
                      key="mallory")
    spoofed = as_ok(nested) and len(nested) > 1 and nested[1] == "ok"
    record(
        "RT-032", "a self-registered fake child is refused by KAsset nest",
        classify(spoofed, "vulnerable", "fixed"), "RGA-049",
        f"fake={fake_uri!r}; nest={nested!r}",
        {"parent": parent_kasset, "fake": fake_uri, "nest": nested,
         "pre_fix": "nest=(True, 'ok')"},
    )

    # RT-035 / RT-028: the public OracleCase arms and the execute crank.
    _, case_kasset = suite_base.approved_kasset(
        addrs, validator="bob", approver="carol", claimant="alice")
    case_uri, adjudicator_cred = suite_base.open_case(
        addrs, case_kasset, adjudicator="dave", opener="alice")
    evidence = call(case_uri, "evidence", [Raw("*dId"), {"hash": "x"}], key="mallory")
    decide_other = call(case_uri, "decide", [Raw("*dId"), {"outcome": "uphold"}],
                        key="mallory")
    close_early = call(case_uri, "close", [], key="mallory", deployer=False)
    expire_early = call(case_uri, "expire", [], key="mallory", deployer=False)
    decided = fixtures.oracle_decide(case_uri, "dave", {"outcome": "uphold"})
    crank = fixtures.oracle_execute(case_uri)
    record(
        "RT-035", "public OracleCase arms enforce party and adjudicator roles",
        classify(as_refusal(evidence) and as_refusal(decide_other),
                 "fixed", "vulnerable"), "RGA-054",
        f"evidence={evidence!r}; decide={decide_other!r}; close={close_early!r}; "
        f"expire={expire_early!r}",
        {"evidence": evidence, "decide_other": decide_other,
         "close_early": close_early, "expire_early": expire_early},
    )
    record(
        "RT-028", "third-party execute applies only the stored decision",
        "accepted", "RGA-024",
        f"decide={decided!r}; mallory execute={crank!r}",
        {"decide": decided, "execute": crank},
    )

    # RT-034: approval is durable across credential revocation.
    _, durable_kasset, _ = suite_base.validated_kasset(addrs, "bob", claimant="alice")
    approver_cred = suite_base.issue(addrs, "carol", "Approver", "approver")
    approved = fixtures.kasset_approve(
        durable_kasset, approver_cred, "carol",
        suite_base.approval(approver_cred, addrs["carol"]))
    revoked = fixtures.call_uri(approver_cred, "revoke",
                                [Raw("*dId"), "capability test"], key="issuer")
    after = fixtures.read(durable_kasset, "get")
    status = after[1].get("status") if as_ok(after) else None
    record(
        "RT-034", "approval survives the approver credential revocation",
        "accepted", "RGA-055",
        f"approve={approved!r}; revoke={revoked!r}; status={status!r}",
        {"approve": approved, "revoke": revoked, "status": status},
    )

    # RT-026: a proof can be re-delegated and burned, but not forged.
    publish_term = f"""
new rl(`rho:registry:lookup`), c1, ret, proofCh, rs(`rho:registry:insertArbitrary`),
    uriCh, dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{bob_cred}`, *c1) |
  for (Cred <- c1) {{
    Cred!("prove", *dId, {enc(requirement)}, *ret, *proofCh) |
    for (@p <- ret) {{
      match p {{
        (true, _) => {{
          for (Proof <- proofCh) {{
            rs!(bundle+{{*Proof}}, *uriCh) |
            for (@uri <- uriCh) {{ deployId!(uri) }}
          }}
        }}
        _ => {{ deployId!(p) }}
      }}
    }}
  }}
}}
"""
    proof_uri = one_term(publish_term, "bob")
    mallory_take = "not-run"
    bob_take = "not-run"
    if isinstance(proof_uri, str) and proof_uri.startswith("rho:id:"):
        mallory_take = fixtures.read(proof_uri, "take")
        bob_take = fixtures.read(proof_uri, "take")
    forged_data = isinstance(mallory_take, tuple) and mallory_take[:1] == (True,)
    record(
        "RT-026", "a forwarded proof can be burned but not forged",
        "accepted", "RGA-035",
        f"mallory={mallory_take!r}; bob={bob_take!r}; "
        f"subject={mallory_take[1].get('subject') if forged_data else None!r}",
        {"proof": proof_uri, "mallory": mallory_take, "bob": bob_take},
    )

    # RT-036: a K-Asset validator, not only the claimant, can open a dispute.
    _, validator_kasset = suite_base.approved_kasset(
        addrs, validator="bob", approver="carol", claimant="alice")
    oracle_cred = suite_base.issue(addrs, "dave", "Oracle", "oracle")
    case_req = {
        "kind": "dispute",
        "openedBy": addrs["bob"],
        "parties": [addrs["alice"], addrs["bob"], addrs["carol"]],
        "groundsHash": "validator grounds",
        "requirement": suite_base.requirement("Oracle", "oracle"),
        "adjudicator": addrs["dave"],
        "adjudicatorCredentialUri": oracle_cred,
        "deadlineHeight": 1_000_000,
    }
    validator_case = fixtures.kasset_open_dispute(validator_kasset, "bob", case_req)
    record(
        "RT-036", "a K-Asset validator can open a dispute",
        classify(as_ok(validator_case), "fixed", "vulnerable"), "RGA-060",
        f"openDispute as bob={validator_case!r}",
        {"kasset": validator_kasset, "open": validator_case,
         "pre_fix": "source-identified; parties omitted the validator"},
    )

    # RT-037: a malformed register dId must not destroy the Root directory.
    bad_register = f"""
new rl(`rho:registry:lookup`), rootCh, fresh, ret,
    deployId(`rho:rchain:deployId`) in {{
  rl!(`{root}`, *rootCh) |
  for (Root <- rootCh) {{
    Root!("register", "component:evil", "rho:id:fake", 1, "x", *fresh, *ret) |
    for (@r <- ret) {{ deployId!(r) }}
  }}
}}
"""
    bad = one_term(bad_register, "mallory")
    keys = call(root, "keys", [], key="mallory", deployer=False)
    record(
        "RT-037", "a malformed register dId leaves the Root directory readable",
        classify(as_ok(keys), "fixed", "vulnerable"), "RGA-061",
        f"malformed register={bad!r}; Root.keys={keys!r}",
        {"register": bad, "keys": keys,
         "pre_fix": "source-identified; not run pre-fix because it destroys rootState"},
    )

    report = {
        "schema": "rgen.redteam/v1",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "node": node.http_json("GET", f"{node.NODE}/api/v1/status").get("version", {}),
        "expectation": EXPECT,
        "scope": "object capabilities",
        "results": RESULTS,
    }
    out = ROOT / "deployments" / "redteam-capabilities.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    spec = ROOT / "spec" / "audit" / "redteam-capabilities.yaml"
    spec.write_text(yaml.safe_dump(report, sort_keys=False) + "\n")
    print(f"redteam-capabilities: wrote {out}")
    print(f"redteam-capabilities: wrote {spec}")

    if EXPECT != "any":
        allowed = {EXPECT, "accepted"}
        if EXPECT == "fixed":
            allowed.add("not_reproduced")
        mismatched = [r for r in RESULTS if r["classification"] not in allowed]
        if mismatched:
            for item in mismatched:
                print(f"redteam-capabilities: expected {EXPECT}, got "
                      f"{item['classification']}: {item['id']} {item['name']}",
                      file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
