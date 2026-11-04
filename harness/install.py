#!/usr/bin/env python3
"""Render and deploy the RGen terms in order.

The r-cash Root URI is read from configs/rcash.json and the r-cash devnet manifest.
`--dry-run` renders only, so static checks can parse the rendered terms without a node.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "tools"))

import deploy as node  # noqa: E402
import preflight  # noqa: E402
from minify_rho import minify  # noqa: E402
from rcash_paths import configured_manifest  # noqa: E402

ORDER = [
    "00_root.rho",
    "01_kernel.rho",
    "02_admin.rho",
    "10_identity.rho",
    "11_credentials.rho",
    "12_token.rho",
    "20_work.rho",
    "21_kasset.rho",
    "22_provenance.rho",
    "30_risk.rho",
    "40_payments.rho",
    "50_oracle.rho",
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
        if "ExprSet" in value:
            return [decode(item) for item in value["ExprSet"]["data"]]
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


def admin_literal(keys: dict, dev_single_key: bool) -> str:
    names = ["admin1", "admin2", "admin3"]
    picked = [keys[name]["public"] for name in names if name in keys]
    distinct = list(dict.fromkeys(picked))
    if len(distinct) < 3:
        if not dev_single_key:
            raise SystemExit(
                "install: need admin1, admin2 and admin3 with distinct keys; "
                "pass --dev-single-key only on a throwaway devnet"
            )
        distinct = [keys["deployer"]["public"]] * 3
    return "[" + ", ".join(f'"{key}".hexToBytes()' for key in distinct[:3]) + "]"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--dev-single-key", action="store_true",
                    help="allow a 2-of-3 set built from one devnet key (never for production)")
    ap.add_argument("--start", default=None,
                    help="resume at this term (requires --root-uri)")
    ap.add_argument("--root-uri", default=None,
                    help="use an existing GenRoot URI instead of deploying 00_root")
    args = ap.parse_args(argv)

    if args.node:
        node.NODE = args.node

    if not args.dry_run and not preflight.require_devnet("install"):
        return 2

    cfg = load_json(ROOT / "configs" / "devnet.json")
    rcash = load_json(ROOT / "configs" / "rcash.json")
    if args.dry_run and not node.keys_path().is_file():
        keys = {
            "deployer": {"address": "1111dryrun", "public": "02" + "11" * 32,
                         "secret": "00" * 32},
            "admin1": {"public": "02" + "22" * 32},
            "admin2": {"public": "02" + "33" * 32},
            "admin3": {"public": "02" + "44" * 32},
        }
    else:
        keys = node.load_keys()
    if "deployer" not in keys:
        raise SystemExit("install: keys file has no deployer key")

    rcash_manifest = configured_manifest(
        cfg.get("rcash_manifest", rcash["root_manifest_path"]))
    if rcash_manifest.is_file():
        rcash_root = load_json(rcash_manifest)["root_uri"]
    elif args.dry_run:
        rcash_root = "rho:id:dryrun-rcash"
    else:
        raise SystemExit(f"install: missing r-cash manifest {rcash_manifest}; "
                         "run `make rcash-bootstrap` first")

    common = {
        "__ADMINS__": admin_literal(keys, args.dev_single_key),
        "__THRESHOLD__": "2",
        "__GENESIS_ISSUER__": keys["deployer"]["address"],
        "__RCASH_ROOT_URI__": rcash_root,
        "__PLATFORM_OWNER__": keys["deployer"]["address"],
    }

    build = ROOT / "contracts" / "build" / "deploy"
    rendered_dir = ROOT / ".devnet" / "rendered"
    rendered_dir.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        for stale in rendered_dir.glob("*.rho"):
            if stale.name not in ORDER:
                stale.unlink()
    state: dict[str, str] = {}
    root_uri = "rho:id:dryrun" if args.dry_run else None
    if args.root_uri:
        root_uri = args.root_uri
        state["root_uri"] = root_uri
    if args.start and not args.dry_run and not root_uri:
        raise SystemExit("install: --start requires --root-uri")
    secret = keys["deployer"]["secret"]
    started = args.start is None or args.dry_run

    for name in ORDER:
        if not started:
            if name != args.start:
                continue
            started = True
        source = build / name
        if not source.is_file():
            raise SystemExit(f"install: missing {source}; run `make build`")
        values = dict(common)
        values["__ROOT_URI__"] = root_uri or "rho:id:pending"
        rendered = render(source.read_text(), values)
        (rendered_dir / name).write_text(rendered)
        term = minify(rendered)
        if len(term.encode()) > 65536:
            raise SystemExit(
                f"install: {name} is {len(term.encode())} bytes after minification; "
                "the node parses at most 65536"
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
            print(f"install: root {root_uri}")
        else:
            state.setdefault("components", {})[name] = decoded

    if not args.dry_run:
        manifest = ROOT / cfg.get("manifest", "deployments/devnet.json")
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({"root_uri": root_uri, **state}, indent=2) + "\n")
        print(f"install: wrote {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
