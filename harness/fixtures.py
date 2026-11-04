"""Typed helpers for the RGen vertical slice and behavioural suites."""

from __future__ import annotations

from assertions import call, one
from terms import Raw
from actors import block_height, resolve as resolve_component

_CACHE: dict[str, str] = {}


def comp(key: str) -> str:
    if key not in _CACHE:
        _CACHE[key] = resolve_component(key)
    return _CACHE[key]


def identity(name: str, handle: str, display: str = ""):
    return call(comp("component:identity"), "register",
                [Raw("*dId"), {"handle": handle, "displayName": display or handle,
                               "orgHash": "", "contactHash": ""}],
                key=name)


def ensure_identity(name: str, handle: str, display: str = ""):
    from actors import address

    subject = address(name)
    reply = call(comp("component:identity"), "profile", [subject], deployer=False)
    if isinstance(reply, tuple) and reply and reply[0] is True:
        return (True, subject)
    return identity(name, handle, display)


def issue(issuer: str, subject: str, ctype: str, discipline: str, jurisdiction: str,
          role: str, level: int = 1, expires_at: int = 0):
    return call(comp("component:credential-book"), "issue",
                [Raw("*dId"), {"subject": subject, "ctype": ctype,
                               "discipline": discipline, "jurisdiction": jurisdiction,
                               "role": role, "level": level, "evidenceHash": "",
                               "parent": None, "expiresAt": expires_at}],
                key=issuer)


def valid(subject: str, ctype: str, discipline: str, jurisdiction: str, role: str,
          min_level: int = 1, key: str = "deployer"):
    return call(comp("component:credential-book"), "valid",
                [subject, {"ctype": ctype, "discipline": discipline,
                           "jurisdiction": jurisdiction, "role": role,
                           "minLevel": min_level}, block_height()],
                key=key, deployer=False)


def open_work(owner: str, title: str, discipline: str, jurisdiction: str = "US-TX"):
    return call(comp("component:work-book"), "openWork",
                [Raw("*dId"), {"titleHash": title, "discipline": discipline,
                               "jurisdiction": jurisdiction, "projectRef": "fixture"}],
                key=owner)


def claim(claimant: str, work_id: str, statement: str, definition: str,
          unit: str = "inspections", value: int = 12):
    return call(comp("component:work-book"), "claim",
                [Raw("*dId"), work_id,
                 {"ctype": "inspection", "statementHash": statement,
                  "definitionHash": definition,
                  "quantity": {"unit": unit, "value": value},
                  "evidence": [{"kind": "photo", "hash": "aa"}],
                  "riskRef": None, "supersedes": None}],
                key=claimant)


def validate(validator: str, claim_id: str, verdict: str = "valid",
             completeness: int = 5, correctness: int = 5,
             traceability: int = 5, fitness: int = 5):
    return call(comp("component:kasset-book"), "validate",
                [Raw("*dId"), claim_id,
                 {"verdict": verdict,
                  "quality": {"completeness": completeness, "correctness": correctness,
                              "traceability": traceability, "fitness": fitness},
                  "characteristicsHash": "bb", "commentHash": "cc",
                  "evidence": [{"kind": "report", "hash": "dd"}]}],
                key=validator)


def approve(approver: str, kasset_id: str, risk_id=None, oracle_case_id=None,
            decision: str = "approve"):
    return call(comp("component:kasset-book"), "approve",
                [Raw("*dId"), kasset_id,
                 {"decision": decision, "conditionsHash": "",
                  "liability": {"responsible": None, "shareBps": 0, "basisHash": ""},
                  "riskId": risk_id, "oracleCaseId": oracle_case_id}],
                key=approver)


def mint(kasset_id: str, key: str = "deployer"):
    return call(comp("component:token"), "mintForKAsset", [kasset_id],
                key=key, deployer=False)


def balance(owner: str, key: str = "deployer"):
    return call(comp("component:token"), "balance", [owner], key=key, deployer=False)


def reputation(owner: str, key: str = "deployer"):
    return call(comp("component:token"), "reputation", [owner], key=key, deployer=False)


def transfer(owner: str, to: str, amount: int, memo: str = "fixture"):
    return call(comp("component:token"), "transfer",
                [Raw("*dId"), to, amount, memo], key=owner)


def assess(assessor: str, subject_id: str, severity: int = 4, probability: int = 3,
           exposure: int = 3, exposure_ref: str = "deck", probability_basis: str = "FMEA",
           consequence_basis: str = "closure", consequence_ref: str = "ee"):
    return call(comp("component:risk-book"), "assess",
                [Raw("*dId"), {"subjectRef": {"type": "kasset", "id": subject_id},
                               "severity": severity, "probability": probability,
                               "exposure": exposure,
                               "discipline": "structural", "jurisdiction": "US-TX",
                               "exposureRef": exposure_ref,
                               "probabilityBasis": probability_basis,
                               "consequenceBasis": consequence_basis,
                               "consequenceRef": consequence_ref,
                               "method": "USCG-SPE", "evidenceHash": ""}],
                key=assessor)


def open_case(opener: str, kind: str, subject_id: str, panel_size: int = 3,
              threshold_bps: int = 6666, payment=None, parties=None):
    return call(comp("component:oracle"), "open",
                [Raw("*dId"), {"kind": kind,
                               "subjectRef": {"type": "kasset", "id": subject_id},
                               "groundsHash": "ff",
                               "requirement": {"ctype": "Oracle", "discipline": "structural",
                                               "jurisdiction": "US-TX", "role": "oracle",
                                               "minLevel": 2, "panelSize": panel_size,
                                               "thresholdBps": threshold_bps},
                               "deadlineHeight": 0,
                               "parties": parties or [opener],
                               "payment": payment, "liability": None,
                               "bondHoldId": None}],
                key=opener)
