#!/usr/bin/env python3
"""Installer state machine: fail after three terms, resume, one entry per component."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import install

DECODED = {
    "component:root": "rho:id:root-test",
    "component:identity-factory": [
        ("identity-factory", "rho:id:if-test"),
        ("identity-directory", "rho:id:id-test")],
    "component:issuer": [
        ("issuer", "rho:id:iss-test"),
        ("credential-factory", "rho:id:cf-test")],
    "component:oracle-factory": [("oracle-factory", "rho:id:of-test")],
    "component:provenance-factory": [("provenance-factory", "rho:id:pf-test")],
    "component:value-proposition-factory": [
        ("value-proposition-factory", "rho:id:vpf-test")],
    "component:claim-factory": [("claim-factory", "rho:id:claim-test")],
}


def decoded_for(term: str):
    # Check the term's own registration marker before the factories it merely resolves.
    order = [
        "component:claim-factory",
        "component:value-proposition-factory",
        "component:provenance-factory",
        "component:oracle-factory",
        "component:issuer",
        "component:identity-factory",
        "component:root",
    ]
    for marker in order:
        if marker in term:
            return DECODED[marker]
    raise AssertionError("fake deploy: no component marker in term")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        (tmp / "configs").mkdir()
        (tmp / "configs" / "devnet.json").write_text(
            json.dumps({"manifest": "deployments/devnet.json"}))
        build = tmp / "contracts" / "build" / "deploy"
        build.mkdir(parents=True)
        for name in install.ORDER:
            shutil.copy(ROOT / "contracts" / "build" / "deploy" / name, build / name)
        keys = {
            "deployer": {"secret": "00" * 32, "address": "1111deployer",
                         "public": "02" + "11" * 32},
            "issuer": {"secret": "11" * 32, "address": "1111issuer",
                       "public": "03" + "22" * 32},
        }
        calls: list[str] = []
        components: dict[str, str] = {}

        def fake_deploy(term: str, secret: str, **kwargs):
            decoded = decoded_for(term)
            if isinstance(decoded, str):
                components["root"] = decoded
            else:
                for key, uri in decoded:
                    components[key] = uri
            calls.append(term[:20])
            return f"deploy-{len(calls)}", decoded

        def fake_resolve(root_uri: str, key: str, secret: str):
            return (True, {"uri": components[key], "kind": install.KINDS[key], "version": 1})

        with mock.patch.object(install, "ROOT", tmp), \
             mock.patch.object(install.node, "deploy_and_wait", fake_deploy), \
             mock.patch.object(install.node, "load_keys", lambda: keys), \
             mock.patch.object(install.node, "keys_path",
                               lambda: tmp / ".devnet" / "keys.json"), \
             mock.patch.object(install.preflight, "require_devnet", lambda _: True), \
             mock.patch.object(install, "resolve_entry", fake_resolve):
            rc = install.main(["--fail-after", "3"])
            if rc != 97:
                print(f"unit_install: expected 97 after three terms, got {rc}")
                return 1
            state = json.loads((tmp / ".devnet" / "install-state.json").read_text())
            if state["complete"] is not False or len(state["terms"]) != 3:
                print(f"unit_install: bad partial state: {state}")
                return 1
            calls.clear()
            rc = install.main([])
            if rc != 0:
                print(f"unit_install: resume failed with {rc}")
                return 1
            state = json.loads((tmp / ".devnet" / "install-state.json").read_text())
            if state["complete"] is not True or len(state["components"]) != 9:
                print(f"unit_install: bad final state: {state}")
                return 1
            if len(calls) != 4:
                print(f"unit_install: resume deployed {len(calls)} terms, expected 4")
                return 1
            manifest = json.loads((tmp / "deployments" / "devnet.json").read_text())
            if (manifest["install"]["status"] != "complete"
                    or len(manifest["components"]) != 9):
                print(f"unit_install: bad manifest: {manifest}")
                return 1
            rendered = (tmp / ".devnet" / "rendered" / "11_credentials.rho").read_text()
            if "1111issuer" not in rendered or '"subject": "1111deployer"' in rendered:
                print("unit_install: issuer address was not separated from the installer")
                return 1

    print("unit_install: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
