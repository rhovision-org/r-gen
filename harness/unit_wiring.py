#!/usr/bin/env python3
"""RGA-070 negative path: a claim term wired to a wrong oracle factory must refuse
to create a K-Asset. The variant factory is real code; only the wiring is wrong."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import assertions
import fixtures
import install
import suite_base
from terms import Raw


def main() -> int:
    if not suite_base.require("unit_wiring"):
        return 2
    addrs = suite_base.setup(("alice", "bob"))
    cred = suite_base.issue(addrs, "bob", "Validator", "validator")
    manifest = json.loads((ROOT / "deployments" / "devnet.json").read_text())
    components = manifest["components"]
    source = (ROOT / "contracts" / "build" / "deploy" / "20_claim.rho").read_text()
    variant = install.minify(install.render(source, {
        "__ROOT_URI__": manifest["root_uri"],
        "__CREDENTIAL_FACTORY_URI__": components["credential-factory"],
        "__VALUE_PROPOSITION_FACTORY_URI__": components["value-proposition-factory"],
        "__ORACLE_FACTORY_URI__": fixtures.fake_uri("oracle"),
    }))
    reply = assertions.one(variant, key="deployer")
    factory_uri = install.uri_map(reply).get("claim-factory")
    if not factory_uri:
        print(f"unit_wiring: variant did not publish a claim factory: {reply!r}")
        return 1

    created = fixtures.call_uri(factory_uri, "create",
                                [Raw("*dId"), suite_base.claim_req(addrs["alice"])],
                                key="alice")
    assertions.expect_ok("variant claim created", created)
    claim_uri = created[1]["uri"]
    reply = fixtures.claim_validate(claim_uri, cred, "bob", suite_base.validation(cred))
    assertions.expect_refusal("wrong oracle wiring refused", reply, "oracle factory")
    state = fixtures.read(claim_uri, "get")[1]
    assertions.expect("no K-Asset on wrong wiring", state.get("kassetRef"), None)
    print("unit_wiring: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
