#!/usr/bin/env python3
"""Render and deploy the r-gen Pareto core in dependency order.

The core is wired at install time: factory URIs are captured from each deploy and rendered
into dependent terms. Core contracts do not resolve GenRoot at runtime; Root is a client
directory only. `--dry-run` renders only, so static checks can parse without a node.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "tools"))

import deploy as node  # noqa: E402
import preflight  # noqa: E402
from minify_rho import minify  # noqa: E402

# 30_oracle needs the credential factory; 22_value needs oracle+credential; 20_claim needs
# oracle+credential+value-proposition factories.
ORDER = [
    "00_root.rho",
    "10_identity.rho",
    "11_credentials.rho",
    "30_oracle.rho",
    "40_provenance.rho",
    "22_value.rho",
    "20_claim.rho",
]


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"install: missing {path}")
    return json.loads(path.read_text())


def render(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace(key, value)
    return text


def decode(value):
    if isinstance(value, list):
        return [decode(item) for item in value]
    if isinstance(value, dict):
        if "ExprString" in value:
            return value["ExprString"]["data"]
        if "ExprUri" in value:
            return value["ExprUri"]["data"]
        if "ExprInt" in value:
            return int(value["ExprInt"]["data"])
        if "ExprBool" in value:
            return bool(value["ExprBool"]["data"])
        if "ExprTuple" in value:
            return tuple(decode(item) for item in value["ExprTuple"]["data"])
        if "ExprList" in value:
            return [decode(item) for item in value["ExprList"]["data"]]
        if "ExprMap" in value:
            data = value["ExprMap"]["data"]
            if isinstance(data, dict):
                return {key: decode(item) for key, item in data.items()}
            return {decode(entry["key"]): decode(entry["value"]) for entry in data}
        if "ExprByteArray" in value:
            return bytes.fromhex(value["ExprByteArray"]["data"])
        return {key: decode(item) for key, item in value.items()}
    return value


def find_uri(value) -> str | None:
    if isinstance(value, str):
        return value if value.startswith("rho:id:") else None
    if isinstance(value, (list, tuple)):
        for item in value:
            found = find_uri(item)
            if found:
                return found
    if isinstance(value, dict):
        for item in value.values():
            found = find_uri(item)
            if found:
                return found
    return None


def uri_map(value) -> dict[str, str]:
    """Collect (key, uri) pairs emitted by a term's deployId."""
    out: dict[str, str] = {}
    if isinstance(value, (list, tuple)):
        for item in value:
            if (isinstance(item, tuple) and len(item) == 2
                    and isinstance(item[0], str) and isinstance(item[1], str)
                    and item[1].startswith("rho:id:")):
                out[item[0]] = item[1]
            else:
                out.update(uri_map(item))
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str) and item.startswith("rho:id:"):
                out[key] = item
            else:
                out.update(uri_map(item))
    return out


COMPONENT_KEYS = [
    "root",
    "identity-factory",
    "identity-directory",
    "issuer",
    "credential-factory",
    "oracle-factory",
    "provenance-factory",
    "value-proposition-factory",
    "claim-factory",
]

# The Root entry for each key carries a kind. The installer verifies the kind as well as
# the URI, so a wrong-kind substitution is a failed install (HZ-DEPLOY-014).
KINDS = {
    "root": "root",
    "identity-factory": "identity",
    "identity-directory": "identity",
    "issuer": "credentials",
    "credential-factory": "credentials",
    "oracle-factory": "oracle",
    "provenance-factory": "provenance",
    "value-proposition-factory": "value",
    "claim-factory": "claims",
}

STATE_SCHEMA = "rgen.install-state/v1"


def state_path() -> Path:
    return ROOT / ".devnet" / "install-state.json"


def plan_hash(build: Path) -> str:
    """Hash the ordered build terms; a changed build invalidates a partial install."""
    digest = hashlib.sha256()
    for name in ORDER:
        digest.update(name.encode())
        digest.update(minify((build / name).read_text()).encode())
    return digest.hexdigest()


def new_state(plan: str) -> dict:
    return {"schema": STATE_SCHEMA, "plan_hash": plan, "root_uri": None,
            "issuer_address": None, "terms": {}, "components": {}, "complete": False}


def issuer_address(keys: dict) -> str:
    """The genesis Issuer may be a distinct key from the installer (RGA-052)."""
    issuer = keys.get("issuer") or keys["deployer"]
    return issuer.get("address", keys["deployer"]["address"])


def load_state(plan: str, allow_any: bool = False) -> dict | None:
    path = state_path()
    if not path.is_file():
        return None
    try:
        state = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        print(f"install: cannot read {path}: {error}")
        return None
    if state.get("schema") != STATE_SCHEMA:
        print(f"install: cannot resume {path}: unknown schema")
        return None
    if not allow_any and state.get("plan_hash") != plan:
        print(f"install: cannot resume {path}: the build changed; reset the devnet or use --fresh")
        return None
    state.setdefault("terms", {})
    state.setdefault("components", {})
    state.setdefault("complete", False)
    return state


def save_state(state: dict) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n")
    os.replace(tmp, path)


def common_values(state: dict) -> dict[str, str]:
    values = {
        "__ROOT_URI__": state.get("root_uri") or "rho:id:dryrun-root",
        "__IDENTITY_DIRECTORY_URI__": state["components"].get(
            "identity-directory", "rho:id:dryrun-identity-directory"),
        "__CREDENTIAL_FACTORY_URI__": state["components"].get(
            "credential-factory", "rho:id:dryrun-credential-factory"),
        "__ORACLE_FACTORY_URI__": state["components"].get(
            "oracle-factory", "rho:id:dryrun-oracle-factory"),
        "__VALUE_PROPOSITION_FACTORY_URI__": state["components"].get(
            "value-proposition-factory", "rho:id:dryrun-value-proposition-factory"),
        "__ISSUER_ADDRESS__": state.get("issuer_address") or "1111dryrun",
    }
    return values


def resolve_key(root_uri: str, key: str, secret: str):
    term = f"""
new rl(`rho:registry:lookup`), ch, ret, deployId(`rho:rchain:deployId`) in {{
  rl!(`{root_uri}`, *ch) |
  for (Root <- ch) {{
    Root!("resolve", "component:{key}", *ret) |
    for (@r <- ret) {{ deployId!(r) }}
  }}
}}
"""
    _, result = node.deploy_and_wait(term, secret, phlo_limit=4_000_000)
    decoded = decode(result)
    if isinstance(decoded, list) and len(decoded) == 1:
        return decoded[0]
    return decoded


def resolve_entry(root_uri: str, key: str, secret: str):
    """Read the Root entry for a key, including its kind."""
    term = f"""
new rl(`rho:registry:lookup`), ch, ret, deployId(`rho:rchain:deployId`) in {{
  rl!(`{root_uri}`, *ch) |
  for (Root <- ch) {{
    Root!("get", "component:{key}", *ret) |
    for (@r <- ret) {{ deployId!(r) }}
  }}
}}
"""
    _, result = node.deploy_and_wait(term, secret, phlo_limit=4_000_000)
    decoded = decode(result)
    if isinstance(decoded, list) and len(decoded) == 1:
        return decoded[0]
    return decoded


def verify_components(root_uri: str, components: dict[str, str], secret: str) -> None:
    """The installer must not write a manifest from a refused Root registration.

    Each term emits its deployId even when GenRoot.register replied (false, reason). Read
    every Root entry before writing the manifest; a missing, different-URI or wrong-kind
    entry is a failed install, not a partial success.
    """
    problems: list[str] = []
    for attempt in range(3):
        problems = []
        for key in COMPONENT_KEYS:
            expected = components.get(key)
            if not expected:
                problems.append(f"{key}: no installer URI")
                continue
            reply = resolve_entry(root_uri, key, secret)
            if not (isinstance(reply, tuple) and len(reply) >= 2 and reply[0] is True):
                problems.append(f"{key}: Root did not resolve it ({reply!r})")
                continue
            entry = reply[1]
            if not isinstance(entry, dict):
                problems.append(f"{key}: Root entry is not a map ({entry!r})")
                continue
            if str(entry.get("uri")) != expected:
                problems.append(f"{key}: Root has {entry.get('uri')!r}, installer has {expected!r}")
            elif entry.get("kind") != KINDS.get(key):
                problems.append(
                    f"{key}: Root kind is {entry.get('kind')!r}, expected {KINDS.get(key)!r}")
            elif entry.get("version") != 1:
                problems.append(f"{key}: Root version is {entry.get('version')!r}, expected 1")
        if not problems:
            print(f"install: Root resolves {len(COMPONENT_KEYS)}/{len(COMPONENT_KEYS)} keys "
                  "with matching URI, kind and version")
            return
        if attempt < 2:
            print("install: Root not consistent yet; retrying in 2s")
            time.sleep(2)
    raise SystemExit("install: Root verification failed: " + "; ".join(problems))


def write_manifest(cfg: dict, state: dict, plan: str) -> None:
    manifest = ROOT / cfg.get("manifest", "deployments/devnet.json")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "root_uri": state["root_uri"],
        "components": state["components"],
        "install": {
            "schema": STATE_SCHEMA,
            "plan_hash": plan,
            "status": "complete" if state.get("complete") else "partial",
            "terms": state.get("terms", {}),
        },
    }
    tmp = manifest.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n")
    os.replace(tmp, manifest)
    print(f"install: wrote {manifest}")


def existing_manifest_state(cfg: dict, plan: str, secret: str) -> dict | None:
    """Use a previously written manifest as state only when it verifies through Root."""
    manifest = ROOT / cfg.get("manifest", "deployments/devnet.json")
    if not manifest.is_file():
        return None
    try:
        old = json.loads(manifest.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    root_uri = old.get("root_uri")
    components = old.get("components")
    if not root_uri or not isinstance(components, dict):
        return None
    old_plan = (old.get("install") or {}).get("plan_hash")
    if old_plan and old_plan != plan:
        print("install: existing manifest is from a different build; reset the devnet or use --fresh")
        raise SystemExit(3)
    try:
        verify_components(root_uri, components, secret)
    except SystemExit as error:
        print(f"install: existing manifest does not verify: {error}")
        print("install: reset the devnet or use --fresh; refusing to create duplicates")
        raise SystemExit(3)
    state = new_state(plan)
    state["root_uri"] = root_uri
    state["components"] = components
    state["complete"] = True
    save_state(state)
    write_manifest(cfg, state, plan)
    return state


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore saved state and install into a fresh devnet")
    ap.add_argument("--fail-after", type=int, default=0,
                    help="test hook: stop after N deploys and save the partial state")
    args = ap.parse_args(argv)

    if args.node:
        node.NODE = args.node
    if not args.dry_run and not preflight.require_devnet("install"):
        return 2

    cfg = load_json(ROOT / "configs" / "devnet.json")
    if args.dry_run and not node.keys_path().is_file():
        keys = {"deployer": {"address": "1111dryrun",
                             "public": "02" + "11" * 32,
                             "secret": "00" * 32}}
    else:
        keys = node.load_keys()
    if "deployer" not in keys:
        raise SystemExit("install: keys file has no deployer key")

    build = ROOT / "contracts" / "build" / "deploy"
    rendered_dir = ROOT / ".devnet" / "rendered"
    rendered_dir.mkdir(parents=True, exist_ok=True)
    plan = plan_hash(build)
    secret = keys["deployer"]["secret"]

    state = None if args.fresh or args.dry_run else load_state(plan)
    if state and state.get("complete"):
        print("install: saved state is complete; verifying")
        verify_components(state["root_uri"], state["components"], secret)
        write_manifest(cfg, state, plan)
        return 0
    if state is None and not args.fresh and not args.dry_run:
        state = existing_manifest_state(cfg, plan, secret)
        if state is not None:
            return 0
    if state is None:
        state = new_state(plan)
    if not state.get("issuer_address"):
        state["issuer_address"] = issuer_address(keys)

    common = common_values(state)
    root_uri = state.get("root_uri")
    deployed = 0

    for name in ORDER:
        if state["terms"].get(name, {}).get("status") == "done":
            print(f"install: {name} already done; skipping")
            continue
        source = build / name
        if not source.is_file():
            raise SystemExit(f"install: missing {source}; run `make build`")
        values = dict(common)
        if root_uri:
            values["__ROOT_URI__"] = root_uri
        rendered = render(source.read_text(), values)
        (rendered_dir / name).write_text(rendered)
        term = minify(rendered)
        if len(term.encode()) > 65536:
            raise SystemExit(
                f"install: {name} is {len(term.encode())} bytes after minification; "
                "the node parses at most 65536"
            )
        if not args.dry_run and "rho:id:dryrun" in term:
            raise SystemExit(
                f"install: {name} still contains a dry-run placeholder; "
                "a component label was missing from the previous deploy"
            )

        if args.dry_run:
            print(f"install: rendered {name} ({len(term.encode())} bytes minified)")
            continue

        deploy_id, result = node.deploy_and_wait(term, secret)
        decoded = decode(result)
        print(f"install: {name} -> {deploy_id}")
        if name == "00_root.rho":
            root_uri = find_uri(decoded)
            if not root_uri:
                raise SystemExit(f"install: could not find root URI in {decoded}")
            state["root_uri"] = root_uri
            state["components"]["root"] = root_uri
            common["__ROOT_URI__"] = root_uri
            print(f"install: root {root_uri}")
        else:
            found = uri_map(decoded)
            state["components"].update(found)
            if "identity-directory" in found:
                common["__IDENTITY_DIRECTORY_URI__"] = found["identity-directory"]
            if "credential-factory" in found:
                common["__CREDENTIAL_FACTORY_URI__"] = found["credential-factory"]
            if "oracle-factory" in found:
                common["__ORACLE_FACTORY_URI__"] = found["oracle-factory"]
            if "value-proposition-factory" in found:
                common["__VALUE_PROPOSITION_FACTORY_URI__"] = found["value-proposition-factory"]
            print(f"install: {name} -> {found}")
        state["terms"][name] = {"deploy_id": deploy_id, "status": "done"}
        save_state(state)
        deployed += 1
        if args.fail_after and deployed >= args.fail_after:
            print(f"install: stopped after {deployed} deploy(s) for testing; state saved")
            return 97

    if not args.dry_run:
        assert root_uri is not None
        verify_components(root_uri, state["components"], secret)
        state["complete"] = True
        save_state(state)
        write_manifest(cfg, state, plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
