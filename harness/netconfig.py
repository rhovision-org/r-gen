#!/usr/bin/env python3
"""Network paths for the r-gen scripts.

`RGEN_NET=devnet` (default) keeps the docker-exec devnet path. `RGEN_NET=testnet`
selects the public testnet profile and its local-only state under `.testnet/`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NET = os.environ.get("RGEN_NET", "devnet")


def _config(name: str) -> dict:
    path = ROOT / "configs" / f"{name}.json"
    return json.loads(path.read_text())


def profile() -> dict:
    if NET == "testnet":
        return _config("testnet")
    return _config("devnet")


def node() -> str:
    return os.environ.get("RGEN_NODE", profile().get("node", "http://localhost:40403"))


def shard() -> str:
    return os.environ.get("RGEN_SHARD", profile().get("shardId", "/root"))


def keys_path() -> Path:
    default = ".testnet/keys.json" if NET == "testnet" else ".devnet/keys.json"
    return ROOT / os.environ.get("RGEN_KEYS", profile().get("keys", default))


def manifest_path() -> Path:
    default = "deployments/testnet.json" if NET == "testnet" else "deployments/devnet.json"
    return ROOT / os.environ.get("RGEN_MANIFEST", profile().get("manifest", default))


def ops_path() -> Path:
    default = ".testnet/ops" if NET == "testnet" else ".devnet/ops"
    return ROOT / os.environ.get("RGEN_OPS", profile().get("ops", default))


def state_path() -> Path:
    default = ".testnet/install.json" if NET == "testnet" else ".devnet/install.json"
    return ROOT / os.environ.get("RGEN_STATE", profile().get("state", default))


def phlo_limit() -> int:
    return int(os.environ.get("RGEN_PHLO_LIMIT", profile().get("phloLimit", 8_000_000)))


def phlo_price() -> int:
    return int(os.environ.get("RGEN_PHLO_PRICE", profile().get("phloPrice", 1)))


def cli_binary() -> Path:
    return ROOT / "target" / "debug" / "rgen-cli"
