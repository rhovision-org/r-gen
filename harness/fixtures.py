"""Core harness helpers for the Pareto primitives.

Calls that need a private capability (a credential, a K-Asset, an oracle case) build a term
that resolves the URI and passes the resulting contract name as a capability, so the callee
checks the relationship rather than trusting a caller-supplied id.
"""

from __future__ import annotations

import sys
import uuid
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


def identity_resume(name: str):
    subject = actors.address(name)
    return call_uri(comp("identity-factory"), "resume", [Raw("*dId"), subject], key=name)


def issue(subject: str, ctype: str, discipline: str, jurisdiction: str, role: str,
          level: int = 1, expires_at: int = 0, issuer: str = "issuer"):
    actors.ensure_vault(issuer)
    req = {
        "subject": subject, "ctype": ctype, "discipline": discipline,
        "jurisdiction": jurisdiction, "role": role, "level": level,
        "evidenceHash": "", "issuerUri": comp("issuer"), "expiresAt": expires_at,
    }
    return call_uri(comp("credential-factory"), "issue", [Raw("*dId"), req], key=issuer)


def cred_check_as(cred_uri: str, caller: str, requirement: dict):
    """Call the advisory `check` arm with an explicit caller address (RGA-027)."""
    term = f"""
new rl(`rho:registry:lookup`), cCh, ret, bd(`rho:block:data`), hCh,
    deployId(`rho:rchain:deployId`) in {{
  rl!(`{cred_uri}`, *cCh) |
  bd!(*hCh) |
  for (Cred <- cCh; @height, @sender, @ts <- hCh) {{
    Cred!("check", "{caller}", {enc(requirement)}, height, *ret) |
    for (@r <- ret) {{ deployId!(r) }}
  }}
}}
"""
    return _one(term, key="deployer")


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
new rl(`rho:registry:lookup`), c1, ret,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{claim_uri}`, *c1) |
  for (Claim <- c1) {{
    Claim!("validate", *dId, "{cred_uri}", {enc(validation)}, *ret) |
    for (@r <- ret) {{ deployId!(r) }}
  }}
}}
"""
    return _one(term, key=validator)


def kasset_approve(kasset_uri: str, cred_uri: str, approver: str, approval: dict):
    term = f"""
new rl(`rho:registry:lookup`), c1, ret,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{kasset_uri}`, *c1) |
  for (KAsset <- c1) {{
    KAsset!("approve", *dId, "{cred_uri}", {enc(approval)}, *ret) |
    for (@r <- ret) {{ deployId!(r) }}
  }}
}}
"""
    return _one(term, key=approver)


def kasset_open_dispute(kasset_uri: str, party: str, case_req: dict):
    return call_uri(kasset_uri, "openDispute", [Raw("*dId"), case_req], key=party)


def oracle_decide(case_uri: str, adjudicator: str, decision: dict):
    term = f"""
new rl(`rho:registry:lookup`), c1, ret,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{case_uri}`, *c1) |
  for (Case <- c1) {{
    Case!("decide", *dId, {enc(decision)}, *ret) |
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


def vp_asset(unit: str = "inspections", mean: int = 12,
             kind: str = "inspection", spec: str = "structural",
             quality_mean: int = 12, quantity_bps: int = 400,
             quality_bps: int = 1200, n: int = 30) -> dict:
    """Dan's quantity/quality/variance description for a value proposition."""
    return {
        "quantity": {"unit": unit, "mean": mean},
        "quality": {"kind": kind, "spec": spec,
                    "scale": {"min": 4, "max": 20}, "mean": quality_mean},
        "variance": {"quantityBps": quantity_bps, "qualityBps": quality_bps, "n": n},
    }


def vp_validate(vp_uri: str, cred_uri: str, validator: str, validation: dict):
    term = f"""
new rl(`rho:registry:lookup`), c1, ret,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{vp_uri}`, *c1) |
  for (VP <- c1) {{
    VP!("validate", *dId, "{cred_uri}", {enc(validation)}, *ret) |
    for (@r <- ret) {{ deployId!(r) }}
  }}
}}
"""
    return _one(term, key=validator)


def provenance_create(subject_uri: str, writers: list, key: str = "deployer"):
    """Create provenance bound to a real subject capability (RGA-022)."""
    term = f"""
new rl(`rho:registry:lookup`), sCh, fCh, ret,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{subject_uri}`, *sCh) |
  rl!(`{comp("provenance-factory")}`, *fCh) |
  for (Subject <- sCh; ProvenanceFactory <- fCh) {{
    ProvenanceFactory!("createBound", *dId, *Subject, {enc(writers)}, *ret) |
    for (@r <- ret) {{ deployId!(r) }}
  }}
}}
"""
    return _one(term, key=key)


def provenance_anchor(prov_uri: str, writer: str, doc: dict):
    return call_uri(prov_uri, "anchor", [Raw("*dId"), doc], key=writer)


def provenance_comment(prov_uri: str, writer: str, comment: dict):
    return call_uri(prov_uri, "comment", [Raw("*dId"), comment], key=writer)


def two_claim_validations(claim_uri: str, cred_uri: str, validator: str, validation: dict):
    """Two validate calls on the same claim in one deploy: exactly one must win."""
    term = f"""
new rl(`rho:registry:lookup`), c1, ret1, ret2,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{claim_uri}`, *c1) |
  for (Claim <- c1) {{
    Claim!("validate", *dId, "{cred_uri}", {enc(validation)}, *ret1) |
    Claim!("validate", *dId, "{cred_uri}", {enc(validation)}, *ret2) |
    for (@a <- ret1; @b <- ret2) {{ deployId!([a, b]) }}
  }}
}}
"""
    return _one(term, key=validator)


def two_kasset_approvals(kasset_uri: str, cred_uri: str, approver: str, approval: dict):
    term = f"""
new rl(`rho:registry:lookup`), c1, ret1, ret2,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{kasset_uri}`, *c1) |
  for (KAsset <- c1) {{
    KAsset!("approve", *dId, "{cred_uri}", {enc(approval)}, *ret1) |
    KAsset!("approve", *dId, "{cred_uri}", {enc(approval)}, *ret2) |
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
             + ", ".join(f"ret{i}" for i in range(n)))
    resolves = " |\n  ".join(f"rl!(`{u}`, *ch{i})" for i, u in enumerate(claim_uris))
    binds = "; ".join(f"C{i} <- ch{i}" for i in range(n))
    calls = " |\n    ".join(
        f'C{i}!("validate", *dId, "{cred_uri}", {enc(validation)}, *ret{i})' for i in range(n))
    joins = "; ".join(f"@a{i} <- ret{i}" for i in range(n))
    results = "[" + ", ".join(f"a{i}" for i in range(n)) + "]"
    term = f"""
new rl(`rho:registry:lookup`), {decls}, dId(`rho:rchain:deployerId`),
    deployId(`rho:rchain:deployId`) in {{
  {resolves} |
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


def cred_prove(cred_uri: str, subject_key: str, requirement: dict):
    """Prove with a credential and take the private one-shot proof once."""
    term = f"""
new rl(`rho:registry:lookup`), c1, ret, proofCh, tCh,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{cred_uri}`, *c1) |
  for (Cred <- c1) {{
    Cred!("prove", *dId, {enc(requirement)}, *ret, *proofCh) |
    for (@p <- ret) {{
      match p {{
        (true, _) => {{
          for (Proof <- proofCh) {{
            Proof!("take", *tCh) |
            for (@t <- tCh) {{ deployId!([(true, "private"), t]) }}
          }}
        }}
        _ => {{ deployId!(p) }}
      }}
    }}
  }}
}}
"""
    return _one(term, key=subject_key)


def cred_prove_twice(cred_uri: str, subject_key: str, requirement: dict):
    """Prove once, then two takes in one deploy: exactly one must return the data."""
    term = f"""
new rl(`rho:registry:lookup`), c1, ret, proofCh, t1, t2,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{cred_uri}`, *c1) |
  for (Cred <- c1) {{
    Cred!("prove", *dId, {enc(requirement)}, *ret, *proofCh) |
    for (@p <- ret) {{
      match p {{
        (true, _) => {{
          for (Proof <- proofCh) {{
            Proof!("take", *t1) | Proof!("take", *t2) |
            for (@a <- t1; @b <- t2) {{ deployId!([a, b]) }}
          }}
        }}
        _ => {{ deployId!(p) }}
      }}
    }}
  }}
}}
"""
    return _one(term, key=subject_key)


def vp_prove_validated(vp_uri: str, caller: str, at_height: int | None = None):
    height_setup = ""
    height_arg = str(at_height) if at_height is not None else "height"
    if at_height is None:
        height_setup = 'bd!(*hCh) | for (@height, @sender, @ts <- hCh) {'
    term = f"""
new rl(`rho:registry:lookup`), c1, ret, proofCh, tCh, bd(`rho:block:data`), hCh,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{vp_uri}`, *c1) |
  {height_setup}
  for (VP <- c1) {{
    VP!("proveValidated", *dId, {height_arg}, *ret, *proofCh) |
    for (@p <- ret) {{
      match p {{
        (true, _) => {{
          for (Proof <- proofCh) {{
            Proof!("take", *tCh) |
            for (@t <- tCh) {{ deployId!([(true, "private"), t]) }}
          }}
        }}
        _ => {{ deployId!(p) }}
      }}
    }}
  }}
  {"" if at_height is not None else "}"}
}}
"""
    return _one(term, key=caller)


def kasset_prove_approved(kasset_uri: str, key: str):
    term = f"""
new rl(`rho:registry:lookup`), c1, ret, proofCh, tCh,
    deployId(`rho:rchain:deployId`) in {{
  rl!(`{kasset_uri}`, *c1) |
  for (KAsset <- c1) {{
    KAsset!("proveApproved", *ret, *proofCh) |
    for (@p <- ret) {{
      match p {{
        (true, _) => {{
          for (Proof <- proofCh) {{
            Proof!("take", *tCh) |
            for (@t <- tCh) {{ deployId!([(true, "private"), t]) }}
          }}
        }}
        _ => {{ deployId!(p) }}
      }}
    }}
  }}
}}
"""
    return _one(term, key=key)


def revoke_credential(cred_uri: str, key: str, reason: str = "test"):
    return call_uri(cred_uri, "revoke", [Raw("*dId"), reason], key=key)


def claim_withdraw(claim_uri: str, key: str):
    return call_uri(claim_uri, "withdraw", [Raw("*dId")], key=key)


def claim_comment(claim_uri: str, key: str, comment: dict):
    return call_uri(claim_uri, "comment", [Raw("*dId"), comment], key=key)


def claim_expire(claim_uri: str):
    return call_uri(claim_uri, "expire", [], deployer=False)


def kasset_reject(kasset_uri: str, cred_uri: str, approver: str, approval: dict):
    term = f"""
new rl(`rho:registry:lookup`), c1, ret,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{kasset_uri}`, *c1) |
  for (KAsset <- c1) {{
    KAsset!("reject", *dId, "{cred_uri}", {enc(approval)}, *ret) |
    for (@r <- ret) {{ deployId!(r) }}
  }}
}}
"""
    return _one(term, key=approver)


def kasset_nest(kasset_uri: str, claimant: str, child_refs: list):
    return call_uri(kasset_uri, "nest", [Raw("*dId"), child_refs], key=claimant)


def kasset_resume_nest(kasset_uri: str, claimant: str):
    return call_uri(kasset_uri, "resumeNest", [Raw("*dId")], key=claimant)


def kasset_abort_nest(kasset_uri: str, claimant: str):
    return call_uri(kasset_uri, "abortNest", [Raw("*dId")], key=claimant)


def claim_resume(claim_uri: str, who: str):
    return call_uri(claim_uri, "resume", [Raw("*dId")], key=who)


def vp_withdraw(vp_uri: str, proposer: str):
    return call_uri(vp_uri, "withdraw", [Raw("*dId")], key=proposer)


def vp_open_dispute(vp_uri: str, party: str, case_req: dict):
    return call_uri(vp_uri, "openDispute", [Raw("*dId"), case_req], key=party)


def vp_comment(vp_uri: str, key: str, comment: dict):
    return call_uri(vp_uri, "comment", [Raw("*dId"), comment], key=key)


def fake_uri(kind: str = "credential") -> str:
    return f"rho:id:forged-{kind}-{uuid.uuid4().hex[:12]}"


def cred_prove_vs_revoke(cred_uri: str, subject_key: str, requirement: dict):
    """Prove and revoke the same credential in one deploy; returns [prove, revoke, take?]."""
    term = f"""
new rl(`rho:registry:lookup`), c1, pRet, rRet, proofCh, tCh,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{cred_uri}`, *c1) |
  for (Cred <- c1) {{
    Cred!("prove", *dId, {enc(requirement)}, *pRet, *proofCh) |
    Cred!("revoke", *dId, "race", *rRet) |
    for (@p <- pRet; @r <- rRet) {{
      match p {{
        (true, _) => {{
          for (Proof <- proofCh) {{
            Proof!("take", *tCh) |
            for (@t <- tCh) {{ deployId!([(true, "private"), r, t]) }}
          }}
        }}
        _ => {{ deployId!([p, r, Nil]) }}
      }}
    }}
  }}
}}
"""
    return _one(term, key=subject_key)


def vp_prove_vs_dispute(vp_uri: str, party: str, case_req: dict, at_height: int = 0):
    term = f"""
new rl(`rho:registry:lookup`), c1, pRet, dRet, proofCh, tCh,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{vp_uri}`, *c1) |
  for (VP <- c1) {{
    VP!("proveValidated", *dId, {at_height}, *pRet, *proofCh) |
    VP!("openDispute", *dId, {enc(case_req)}, *dRet) |
    for (@p <- pRet; @d <- dRet) {{
      match p {{
        (true, _) => {{
          for (Proof <- proofCh) {{
            Proof!("take", *tCh) |
            for (@t <- tCh) {{ deployId!([(true, "private"), d, t]) }}
          }}
        }}
        _ => {{ deployId!([p, d, Nil]) }}
      }}
    }}
  }}
}}
"""
    return _one(term, key=party)


def oracle_decide_vs_expire(case_uri: str, adjudicator: str, decision: dict):
    term = f"""
new rl(`rho:registry:lookup`), c1, dRet, eRet,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{case_uri}`, *c1) |
  for (Case <- c1) {{
    Case!("decide", *dId, {enc(decision)}, *dRet) |
    Case!("expire", *eRet) |
    for (@d <- dRet; @e <- eRet) {{ deployId!([d, e]) }}
  }}
}}
"""
    return _one(term, key=adjudicator)


def two_identity_creates(name: str, handle: str):
    term = f"""
new rl(`rho:registry:lookup`), c1, r1, r2,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{comp("identity-factory")}`, *c1) |
  for (F <- c1) {{
    F!("create", *dId, {{"handle": "{handle}-a", "displayNameHash": "",
                        "orgHash": "", "contactHash": ""}}, *r1) |
    F!("create", *dId, {{"handle": "{handle}-b", "displayNameHash": "",
                        "orgHash": "", "contactHash": ""}}, *r2) |
    for (@a <- r1; @b <- r2) {{ deployId!([a, b]) }}
  }}
}}
"""
    return _one(term, key=name)


def two_nests_same_parent(parent_uri: str, claimant: str, child_refs: list):
    term = f"""
new rl(`rho:registry:lookup`), c1, r1, r2,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{parent_uri}`, *c1) |
  for (P <- c1) {{
    P!("nest", *dId, {enc(child_refs)}, *r1) |
    P!("nest", *dId, {enc(child_refs)}, *r2) |
    for (@a <- r1; @b <- r2) {{ deployId!([a, b]) }}
  }}
}}
"""
    return _one(term, key=claimant)
