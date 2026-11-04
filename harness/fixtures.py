"""Core harness helpers for the Pareto primitives.

Calls that need a private capability (a credential, a K-Asset, an oracle case) build a term
that resolves the URI and passes the resulting contract name as a capability, so the callee
checks the relationship rather than trusting a caller-supplied id.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import actors
import assertions
from terms import Raw, enc, q


def comp(key: str) -> str:
    return assertions.manifest()["components"][key]


def _one(term: str, key: str = "deployer"):
    return assertions.one(term, key=key)


def call_uri(uri: str, arm: str, args=None, key: str = "deployer", deployer: bool = True):
    from terms import call_term, call_no_deployer
    term = call_term(uri, arm, args or ()) if deployer else call_no_deployer(uri, arm, args or ())
    return _one(term, key=key)


def read(uri: str, arm: str, args=None):
    return call_uri(uri, arm, args or [], deployer=False)


def identity(name: str, handle: str, display: str = ""):
    profile = {"handle": handle, "displayNameHash": display, "orgHash": "", "contactHash": ""}
    return call_uri(comp("identity-factory"), "create", [Raw("*dId"), profile], key=name)


def ensure_identity(name: str, handle: str, display: str = ""):
    subject = actors.address(name)
    reply = call_uri(comp("identity-directory"), "lookup", [subject], deployer=False)
    if isinstance(reply, tuple) and reply and reply[0] is True:
        return (True, subject)
    return identity(name, handle, display)


def issue(subject: str, ctype: str, discipline: str, jurisdiction: str, role: str,
          level: int = 1, expires_at: int = 0, issuer: str = "deployer"):
    req = {
        "subject": subject, "ctype": ctype, "discipline": discipline,
        "jurisdiction": jurisdiction, "role": role, "level": level,
        "evidenceHash": "", "issuerUri": comp("issuer"), "expiresAt": expires_at,
    }
    return call_uri(comp("credential-factory"), "issue", [Raw("*dId"), req], key=issuer)


def cred_check(cred_uri: str, subject_key: str, requirement: dict):
    term = f"""
new rl(`rho:registry:lookup`), cCh, ret, bd(`rho:block:data`), hCh,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{cred_uri}`, *cCh) |
  bd!(*hCh) |
  for (Cred <- cCh; @height, @sender, @ts <- hCh) {{
    Cred!("check", *dId, {enc(requirement)}, height, *ret) |
    for (@r <- ret) {{ deployId!(r) }}
  }}
}}
"""
    return _one(term, key=subject_key)


def claim(claimant: str, req: dict):
    return call_uri(comp("claim-factory"), "create", [Raw("*dId"), req], key=claimant)


def claim_validate(claim_uri: str, cred_uri: str, validator: str, validation: dict):
    term = f"""
new rl(`rho:registry:lookup`), c1, c2, ret,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{claim_uri}`, *c1) | rl!(`{cred_uri}`, *c2) |
  for (Claim <- c1; Cred <- c2) {{
    Claim!("validate", *dId, *Cred, {enc(validation)}, *ret) |
    for (@r <- ret) {{ deployId!(r) }}
  }}
}}
"""
    return _one(term, key=validator)


def kasset_approve(kasset_uri: str, cred_uri: str, approver: str, approval: dict):
    term = f"""
new rl(`rho:registry:lookup`), c1, c2, ret,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{kasset_uri}`, *c1) | rl!(`{cred_uri}`, *c2) |
  for (KAsset <- c1; Cred <- c2) {{
    KAsset!("approve", *dId, *Cred, {enc(approval)}, *ret) |
    for (@r <- ret) {{ deployId!(r) }}
  }}
}}
"""
    return _one(term, key=approver)


def kasset_open_dispute(kasset_uri: str, party: str, case_req: dict):
    return call_uri(kasset_uri, "openDispute", [Raw("*dId"), case_req], key=party)


def oracle_decide(case_uri: str, cred_uri: str, adjudicator: str, decision: dict):
    term = f"""
new rl(`rho:registry:lookup`), c1, c2, ret,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{case_uri}`, *c1) | rl!(`{cred_uri}`, *c2) |
  for (Case <- c1; Cred <- c2) {{
    Case!("decide", *dId, *Cred, {enc(decision)}, *ret) |
    for (@r <- ret) {{ deployId!(r) }}
  }}
}}
"""
    return _one(term, key=adjudicator)


def oracle_execute(case_uri: str):
    return call_uri(case_uri, "execute", [], deployer=False)


def vp_propose(proposer: str, req: dict):
    return call_uri(comp("value-proposition-factory"), "propose",
                    [Raw("*dId"), req], key=proposer)


def vp_validate(vp_uri: str, cred_uri: str, validator: str, validation: dict):
    term = f"""
new rl(`rho:registry:lookup`), c1, c2, ret,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{vp_uri}`, *c1) | rl!(`{cred_uri}`, *c2) |
  for (VP <- c1; Cred <- c2) {{
    VP!("validate", *dId, *Cred, {enc(validation)}, *ret) |
    for (@r <- ret) {{ deployId!(r) }}
  }}
}}
"""
    return _one(term, key=validator)


def provenance_create(asset_ref: dict, writers: list):
    return call_uri(comp("provenance-factory"), "create",
                    [asset_ref, writers], deployer=False)


def provenance_anchor(prov_uri: str, writer: str, doc: dict):
    return call_uri(prov_uri, "anchor", [Raw("*dId"), doc], key=writer)


def two_claim_validations(claim_uri: str, cred_uri: str, validator: str, validation: dict):
    """Two validate calls on the same claim in one deploy: exactly one must win."""
    term = f"""
new rl(`rho:registry:lookup`), c1, c2, ret1, ret2,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{claim_uri}`, *c1) | rl!(`{cred_uri}`, *c2) |
  for (Claim <- c1; Cred <- c2) {{
    Claim!("validate", *dId, *Cred, {enc(validation)}, *ret1) |
    Claim!("validate", *dId, *Cred, {enc(validation)}, *ret2) |
    for (@a <- ret1; @b <- ret2) {{ deployId!([a, b]) }}
  }}
}}
"""
    return _one(term, key=validator)


def two_kasset_approvals(kasset_uri: str, cred_uri: str, approver: str, approval: dict):
    term = f"""
new rl(`rho:registry:lookup`), c1, c2, ret1, ret2,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{kasset_uri}`, *c1) | rl!(`{cred_uri}`, *c2) |
  for (KAsset <- c1; Cred <- c2) {{
    KAsset!("approve", *dId, *Cred, {enc(approval)}, *ret1) |
    KAsset!("approve", *dId, *Cred, {enc(approval)}, *ret2) |
    for (@a <- ret1; @b <- ret2) {{ deployId!([a, b]) }}
  }}
}}
"""
    return _one(term, key=approver)


def two_oracle_executes(case_uri: str):
    term = f"""
new rl(`rho:registry:lookup`), c1, ret1, ret2,
    deployId(`rho:rchain:deployId`) in {{
  rl!(`{case_uri}`, *c1) |
  for (Case <- c1) {{
    Case!("execute", *ret1) |
    Case!("execute", *ret2) |
    for (@a <- ret1; @b <- ret2) {{ deployId!([a, b]) }}
  }}
}}
"""
    return _one(term)


def two_comments(claim_uri: str, key: str, comment: dict):
    term = f"""
new rl(`rho:registry:lookup`), c1, ret1, ret2,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{claim_uri}`, *c1) |
  for (Claim <- c1) {{
    Claim!("comment", *dId, {enc(comment)}, *ret1) |
    Claim!("comment", *dId, {enc(comment)}, *ret2) |
    for (@a <- ret1; @b <- ret2) {{ deployId!([a, b]) }}
  }}
}}
"""
    return _one(term, key=key)


def n_claim_validations(claim_uris: list[str], cred_uri: str, validator: str,
                        validation: dict):
    n = len(claim_uris)
    decls = (", ".join(f"ch{i}" for i in range(n)) + ", "
             + ", ".join(f"ret{i}" for i in range(n)) + ", cc")
    resolves = " |\n  ".join(f"rl!(`{u}`, *ch{i})" for i, u in enumerate(claim_uris))
    cred = f"rl!(`{cred_uri}`, *cc)"
    binds = "Cred <- cc" + "".join(f"; C{i} <- ch{i}" for i in range(n))
    calls = " |\n    ".join(
        f'C{i}!("validate", *dId, *Cred, {enc(validation)}, *ret{i})' for i in range(n))
    joins = "; ".join(f"@a{i} <- ret{i}" for i in range(n))
    results = "[" + ", ".join(f"a{i}" for i in range(n)) + "]"
    term = f"""
new rl(`rho:registry:lookup`), {decls}, dId(`rho:rchain:deployerId`),
    deployId(`rho:rchain:deployId`) in {{
  {resolves} |
  {cred} |
  for ({binds}) {{
    {calls} |
    for ({joins}) {{ deployId!({results}) }}
  }}
}}
"""
    return _one(term, key=validator)


def claim_req(claimant: str, *, statement: str = "deck inspected",
              definition: str = "twelve inspections", discipline: str = "structural",
              jurisdiction: str = "US-TX", value: int = 12,
              value_proposition: dict | None = None):
    return {
        "work": {"titleHash": "bridge-deck", "discipline": discipline,
                 "jurisdiction": jurisdiction, "projectRef": "fixture"},
        "selectionCriteria": {"ctype": "Validator", "discipline": discipline,
                              "jurisdiction": jurisdiction, "role": "validator",
                              "minLevel": 1},
        "selectionCriteriaHash": "sc",
        "statementHash": statement,
        "definitionHash": definition,
        "quantity": {"unit": "inspections", "value": value},
        "evidence": [{"kind": "photo", "hash": "aa"}],
        "valuePropositionRef": value_proposition,
        "deadlineHeight": 0,
        "commentUntilHeight": 0,
    }
