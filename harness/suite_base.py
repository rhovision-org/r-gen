"""Shared setup for the per-primitive suites."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import actors
import assertions
import fixtures
import preflight

ACTORS = ("alice", "bob", "carol", "dave", "frank")


def require(label: str) -> bool:
    return preflight.require_devnet(label)


def setup(names=ACTORS) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    addrs: dict[str, str] = {}
    for name in names:
        actors.ensure_vault(name)
        assertions.expect_ok(f"{name} identity",
                             fixtures.ensure_identity(name, f"{name}-{suffix}"))
        addrs[name] = actors.address(name)
    return addrs


def issue(addrs: dict[str, str], name: str, ctype: str, role: str,
          discipline: str = "structural", jurisdiction: str = "US-TX",
          level: int = 1, expires_at: int = 0) -> str:
    reply = fixtures.issue(addrs[name], ctype, discipline, jurisdiction, role, level,
                           expires_at)
    assertions.expect_ok(f"{name} {ctype} credential", reply)
    return reply[1]


def requirement(ctype: str, role: str, discipline: str = "structural",
                jurisdiction: str = "US-TX", min_level: int = 1) -> dict:
    return {"ctype": ctype, "discipline": discipline, "jurisdiction": jurisdiction,
            "role": role, "minLevel": min_level}


def validation(cred_uri: str, verdict: str = "valid") -> dict:
    return {
        "verdict": verdict,
        "quality": {"completeness": 5, "correctness": 5,
                    "traceability": 5, "fitness": 5},
        "credentialUri": cred_uri,
        "characteristicsHash": "chars",
        "commentHash": "comments",
        "evidence": [],
    }


def approval(cred_uri: str, approver_address: str) -> dict:
    return {
        "decision": "approve",
        "conditionsHash": "",
        "credentialUri": cred_uri,
        "liability": {"responsible": approver_address, "shareBps": 10000,
                      "basisHash": "liability"},
    }


def claim_req(claimant: str, vp_uri: str | None = None) -> dict:
    req = fixtures.claim_req(claimant,
                             value_proposition=({"id": vp_uri, "uri": vp_uri}
                                                if vp_uri else None))
    req["deadlineHeight"] = 1000000
    req["commentUntilHeight"] = 1000000
    return req


def validated_kasset(addrs: dict[str, str], validator: str, claimant: str = "alice",
                     vp_uri: str | None = None) -> tuple[str, str, str]:
    """Create a claim, validate it with `validator`, and return (claim, kasset, cred)."""
    validator_cred = issue(addrs, validator, "Validator", "validator")
    claim_reply = fixtures.claim(claimant, claim_req(addrs[claimant], vp_uri))
    assertions.expect_ok("claim created", claim_reply)
    claim_uri = claim_reply[1]["uri"]
    reply = fixtures.claim_validate(claim_uri, validator_cred, validator,
                                    validation(validator_cred))
    assertions.expect_ok("claim validated", reply)
    return claim_uri, reply[1]["uri"], validator_cred


def approved_kasset(addrs: dict[str, str], validator: str = "bob",
                    approver: str = "carol", vp_uri: str | None = None) -> tuple[str, str]:
    claim_uri, kasset_uri, _ = validated_kasset(addrs, validator, vp_uri=vp_uri)
    approver_cred = issue(addrs, approver, "Approver", "approver")
    reply = fixtures.kasset_approve(kasset_uri, approver_cred, approver,
                                    approval(approver_cred, addrs[approver]))
    assertions.expect_ok("K-Asset approved", reply)
    return claim_uri, kasset_uri


def open_case(addrs: dict[str, str], kasset_uri: str, adjudicator: str = "dave",
              opener: str = "alice") -> tuple[str, str]:
    adjudicator_cred = issue(addrs, adjudicator, "Oracle", "oracle")
    case_req = {
        "kind": "dispute",
        "openedBy": addrs[opener],
        "parties": [addrs["alice"], addrs["bob"]],
        "groundsHash": "grounds",
        "requirement": requirement("Oracle", "oracle"),
        "adjudicator": addrs[adjudicator],
        "adjudicatorCredentialUri": adjudicator_cred,
        "deadlineHeight": 1000000,
    }
    opened = fixtures.kasset_open_dispute(kasset_uri, opener, case_req)
    assertions.expect_ok("dispute opened", opened)
    return opened[1]["uri"], adjudicator_cred
