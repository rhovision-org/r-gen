#!/usr/bin/env python3
"""Read-only identity and safety preflight for the public r-gen testnet.

Pins the network id, shard and genesis block; checks that the node accepts deploys and
that the local key file is fresh, owner-only and untracked. Writes no chain state.

Exit codes: 0 ok, 2 identity mismatch, 3 unsafe keys, 4 node unavailable.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LIVE_HINTS = ("rhobot.net", "164.90.140.144", "167.99.43.214")
DEVNET_KEYS = ROOT / ".devnet" / "keys.json"


class PreflightError(RuntimeError):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


def get(base: str, path: str) -> object:
    request = urllib.request.Request(f"{base.rstrip('/')}{path}")
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read())


def genesis(base: str) -> dict:
    value = get(base, "/api/blocks/0/0")
    if isinstance(value, list):
        if not value:
            raise PreflightError(2, "genesis block list is empty")
        return value[0]
    if isinstance(value, dict):
        return value
    raise PreflightError(2, f"genesis block shape: {type(value).__name__}")


def tracked(path: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_keys(path: Path) -> dict:
    if not path.is_file():
        return {"present": False, "path": str(path)}
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise PreflightError(3, f"{path} is mode {mode:o}; expected 0600")
    if tracked(path):
        raise PreflightError(3, f"{path} is tracked by git")
    try:
        keys = json.loads(path.read_text())
    except ValueError as error:
        raise PreflightError(3, f"{path}: {error}") from error
    if "deployer" not in keys:
        raise PreflightError(3, f"{path} has no deployer key")
    devnet = json.loads(DEVNET_KEYS.read_text()) if DEVNET_KEYS.is_file() else {}
    devnet_public = {entry.get("public") for entry in devnet.values() if isinstance(entry, dict)}
    reused = [name for name, entry in keys.items()
              if isinstance(entry, dict) and entry.get("public") in devnet_public]
    if reused:
        raise PreflightError(3, f"testnet key file reuses devnet keys: {reused}")
    return {
        "present": True,
        "path": str(path),
        "mode": f"{mode:o}",
        "names": sorted(keys),
        "deployer": keys["deployer"].get("address"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", default=None)
    parser.add_argument("--keys", type=Path, default=ROOT / ".testnet" / "keys.json")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--out", type=Path, default=ROOT / ".testnet" / "preflight.json")
    args = parser.parse_args()

    profile = json.loads((ROOT / "configs" / "testnet.json").read_text())
    node = args.node or os.environ.get("RGEN_NODE") or profile["node"]
    if any(hint in node for hint in LIVE_HINTS) and not args.allow_live:
        print("testnet-preflight: live rhobot endpoint; pass --allow-live", file=sys.stderr)
        return 2
    try:
        status = get(node, "/api/v1/status")
        block0 = genesis(node)
        last = get(node, "/api/last-finalized-block").get("blockInfo", {})
        health = get(node, "/health")
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as error:
        print(f"testnet-preflight: node unavailable: {error}", file=sys.stderr)
        return 4

    if status.get("networkId") != profile["networkId"]:
        print(
            f"testnet-preflight: networkId {status.get('networkId')} != {profile['networkId']}",
            file=sys.stderr,
        )
        return 2
    if status.get("shardId") != profile["shardId"]:
        print(
            f"testnet-preflight: shardId {status.get('shardId')} != {profile['shardId']}",
            file=sys.stderr,
        )
        return 2
    if block0.get("blockHash") != profile["genesisBlockHash"]:
        print(
            f"testnet-preflight: genesis {block0.get('blockHash')} != "
            f"{profile['genesisBlockHash']} (reset?)",
            file=sys.stderr,
        )
        return 2
    if not status.get("acceptsDeploys"):
        print("testnet-preflight: node does not accept deploys", file=sys.stderr)
        return 4
    if status.get("degraded") not in (None, "normal"):
        print(f"testnet-preflight: node degraded: {status.get('degraded')}", file=sys.stderr)
        return 4
    if int(status.get("minPhloPrice", 1)) > int(profile.get("phloPrice", 1)):
        print("testnet-preflight: phlo price below minPhloPrice", file=sys.stderr)
        return 4
    if not health.get("ok", False):
        print("testnet-preflight: /health is not ok", file=sys.stderr)
        return 4

    try:
        keys = check_keys(args.keys)
    except PreflightError as error:
        print(f"testnet-preflight: {error}", file=sys.stderr)
        return error.code

    report = {
        "node": node,
        "networkId": status.get("networkId"),
        "shardId": status.get("shardId"),
        "genesis": block0.get("blockHash"),
        "nodeBuild": (status.get("version") or {}).get("node"),
        "latestBlockNumber": status.get("latestBlockNumber"),
        "lastFinalized": last.get("blockNumber"),
        "acceptsDeploys": status.get("acceptsDeploys"),
        "degraded": status.get("degraded"),
        "minPhloPrice": status.get("minPhloPrice"),
        "faucet": profile.get("faucetUrl"),
        "faucetAmount": profile.get("faucetAmount"),
        "keys": keys,
        "buildWarning": (
            None
            if profile.get("nodeBuildObserved", "") in str((status.get("version") or {}).get("node"))
            else f"node build differs from observed {profile.get('nodeBuildObserved')}"
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"testnet-preflight: ok network={report['networkId']} shard={report['shardId']} "
        f"height={report['latestBlockNumber']} keys={keys.get('present')}"
    )
    if report["buildWarning"]:
        print(f"testnet-preflight: warning: {report['buildWarning']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
