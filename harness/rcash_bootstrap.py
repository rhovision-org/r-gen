#!/usr/bin/env python3
"""Bring the local r-cash rail up far enough for r-share.

The pinned r-cash installer currently stops at its `51_pool` step (the node's parser depth).
r-share needs only the r-cash Root, clock, asset resolver and account factory, so this
script:

1. builds the r-cash CLI if needed and runs its installer, tolerating a late failure;
2. runs the r-cash `09_identity` step if `component:account-factory` is absent;
3. repairs `deployments/devnet-v4.json` from the install state, because the r-cash
   installer writes its manifest only at the end.

It exits 0 only when the Root and `component:account-factory` resolve.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))
from rcash_paths import rcash_dir  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rcash", default=str(rcash_dir()))
    ap.add_argument("--node", default="http://localhost:40403")
    ap.add_argument("--min-lock-blocks", default="10")
    args = ap.parse_args(argv)

    rcash = Path(args.rcash).resolve()
    if not (rcash / "Cargo.toml").is_file():
        print(f"rcash-bootstrap: not an r-cash checkout: {rcash}", file=sys.stderr)
        return 1
    if not (rcash / "target" / "debug" / "rcash").is_file():
        print("rcash-bootstrap: building rcash-cli")
        build = subprocess.run(
            ["cargo", "build", "--manifest-path", str(rcash / "Cargo.toml"),
             "-p", "rcash-cli"],
            text=True,
        )
        if build.returncode != 0:
            print("rcash-bootstrap: rcash build failed", file=sys.stderr)
            return 1

    print("rcash-bootstrap: running the r-cash installer")
    install = subprocess.run(
        ["make", "-C", str(rcash), "install"], text=True,
    )
    state_path = rcash / ".devnet" / "v3-install.json"
    if not state_path.is_file():
        print(f"rcash-bootstrap: installer wrote no state at {state_path}", file=sys.stderr)
        return 1
    if install.returncode != 0:
        print("rcash-bootstrap: r-cash installer stopped early; checking the rail")

    sys.path.insert(0, str(rcash / "harness"))
    try:
        from install_testnet import Installer, STEP_KEYS  # type: ignore
    except Exception as error:  # pragma: no cover - broken r-cash checkout
        print(f"rcash-bootstrap: cannot import the r-cash installer: {error}",
              file=sys.stderr)
        return 1

    inst = Installer(
        node_url=args.node,
        allow_live=False,
        keys_path=rcash / ".devnet" / "keys.json",
        state_path=state_path,
        ops_path=rcash / ".devnet" / "ops",
        admin_keys_path=rcash / ".devnet" / "keys.json",
        manifest_path=rcash / "deployments" / "devnet-v4.json",
        min_lock_blocks=args.min_lock_blocks,
        shard_id="/root",
        phlo_limit=4_000_000,
        phlo_price=1,
    )
    inst.state = json.loads(state_path.read_text())
    inst.root_uri = inst.state.get("root_uri")
    if not inst.root_uri:
        print("rcash-bootstrap: no r-cash Root URI in the install state", file=sys.stderr)
        return 1

    tip = inst.chain.last_finalized_block().get("blockHash")
    present = inst.resolved(tip, STEP_KEYS["identity"])
    if "missing" in present:
        print("rcash-bootstrap: installing the account factory")
        resolver = inst.state["steps"]["14_asset_resolver"]["uris"]
        try:
            inst.step("09_identity", "testnet:identity",
                      {"__ROOT_URI__": inst.root_uri,
                       "__ASSET_RESOLVER_URI__": resolver[0]},
                      STEP_KEYS["identity"], tip)
        except SystemExit as error:
            print(f"rcash-bootstrap: identity step failed: {error}", file=sys.stderr)
            return 1
        inst.save()

    # Repair the manifest from the state; the installer writes it only at the very end.
    manifest_path = rcash / "deployments" / "devnet-v4.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    manifest["root_uri"] = inst.state["root_uri"]
    identity = inst.state.get("steps", {}).get("09_identity", {}).get("uris", [])
    if identity:
        manifest["account_factory_uri"] = identity[0]
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    present = inst.resolved(tip, ["rcash:root", *STEP_KEYS["identity"]])
    if "missing" in present:
        print(f"rcash-bootstrap: rail incomplete: {present}", file=sys.stderr)
        return 1
    print(f"rcash-bootstrap: root {inst.state['root_uri']}")
    print(f"rcash-bootstrap: account factory {identity[0] if identity else 'present'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
