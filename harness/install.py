#!/usr/bin/env python3
"""Render and deploy the r-gen Pareto core in dependency order.

The core is wired at install time: factory URIs are captured from each deploy and rendered
into dependent terms. Core contracts do not resolve GenRoot at runtime; Root is a client
directory only. `--dry-run` renders only, so static checks can parse without a node.
"""

from __future__ import annotations

import argparse
import json
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


def verify_components(root_uri: str, components: dict[str, str], secret: str) -> None:
    """The installer must not write a manifest from a refused Root registration.

    Each term emits its deployId even when GenRoot.register replied (false, reason). Resolve
    every key through Root before writing the manifest; a missing or different URI is a failed
    install, not a partial success.
    """
    problems: list[str] = []
    for attempt in range(3):
        problems = []
        for key in COMPONENT_KEYS:
            expected = components.get(key)
            if not expected:
                problems.append(f"{key}: no installer URI")
                continue
            reply = resolve_key(root_uri, key, secret)
            if not (isinstance(reply, tuple) and len(reply) >= 2 and reply[0] is True):
                problems.append(f"{key}: Root did not resolve it ({reply!r})")
            elif str(reply[1]) != expected:
                problems.append(f"{key}: Root has {reply[1]!r}, installer has {expected!r}")
        if not problems:
            print(f"install: Root resolves {len(COMPONENT_KEYS)}/{len(COMPONENT_KEYS)} keys")
            return
        if attempt < 2:
            print("install: Root not consistent yet; retrying in 2s")
            time.sleep(2)
    raise SystemExit("install: Root verification failed: " + "; ".join(problems))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", default=None)
    ap.add_argument("--dry-run", action="store_true")
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

    common = {
        "__ROOT_URI__": "rho:id:dryrun-root",
        "__IDENTITY_DIRECTORY_URI__": "rho:id:dryrun-identity-directory",
        "__CREDENTIAL_FACTORY_URI__": "rho:id:dryrun-credential-factory",
        "__ORACLE_FACTORY_URI__": "rho:id:dryrun-oracle-factory",
        "__VALUE_PROPOSITION_FACTORY_URI__": "rho:id:dryrun-value-proposition-factory",
    }

    build = ROOT / "contracts" / "build" / "deploy"
    rendered_dir = ROOT / ".devnet" / "rendered"
    rendered_dir.mkdir(parents=True, exist_ok=True)
    state: dict[str, object] = {"components": {}}
    root_uri = None
    secret = keys["deployer"]["secret"]

    for name in ORDER:
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

    if not args.dry_run:
        assert root_uri is not None
        verify_components(root_uri, state["components"], secret)
        manifest = ROOT / cfg.get("manifest", "deployments/devnet.json")
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(state, indent=2) + "\n")
        print(f"install: wrote {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
