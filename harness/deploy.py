#!/usr/bin/env python3
"""Submit and read Rholang on the local rholo devnet.

Deploys go through the node's own CLI inside `devnet-bootstrap`, so deploy signing is not
reimplemented in Python. Reads use the public HTTP API.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path


def _devnet_config() -> dict:
    path = Path(__file__).resolve().parent.parent / "configs" / "devnet.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


_CFG = _devnet_config()
ROOT = Path(__file__).resolve().parent.parent
REMOTE = os.environ.get("RGEN_REMOTE") == "1"
NODE = os.environ.get("RGEN_NODE", _CFG.get("node", "http://localhost:40403"))
ADMIN = os.environ.get("RGEN_ADMIN", _CFG.get("admin_node", "http://localhost:40405"))
CONTAINER = os.environ.get("RGEN_CONTAINER", "devnet-bootstrap")
SHARD = os.environ.get("RGEN_SHARD", _CFG.get("shard_id", "/root"))
PHLO_LIMIT = int(os.environ.get("RGEN_PHLO_LIMIT", _CFG.get("phlo_limit", 8000000)))
PHLO_PRICE = int(os.environ.get("RGEN_PHLO_PRICE", _CFG.get("phlo_price", 1)))
FAUCET_URL = os.environ.get("RGEN_FAUCET_URL", f"{NODE}/api/v1/faucet")
CLI = ROOT / "target" / "debug" / "rgen-cli"
OPS = Path(os.environ.get("RGEN_OPS", str(ROOT / (".testnet/ops" if REMOTE else ".devnet/ops"))))
MANIFEST = Path(
    os.environ.get(
        "RGEN_MANIFEST",
        str(ROOT / ("deployments/testnet.json" if REMOTE else "deployments/devnet.json")),
    )
)
DEPLOY_RE = re.compile(r"DeployId is:\s*([0-9a-fA-F]+)")


class DevnetError(RuntimeError):
    pass


def http_json(method: str, url: str, body=None, timeout: float = 30.0):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
    return json.loads(raw) if raw.strip() else {}


def height() -> int:
    return int(http_json("GET", f"{NODE}/api/v1/status")["latestBlockNumber"])


def docker_exec(args: list[str], input_text: str | None = None,
                timeout: float = 180.0) -> subprocess.CompletedProcess:
    cmd = ["docker", "exec", "-i", CONTAINER, *args]
    return subprocess.run(cmd, input=input_text, text=True, capture_output=True,
                          timeout=timeout)


def write_term(term: str) -> str:
    path = f"/tmp/rgen-{uuid.uuid4().hex}.rho"
    proc = docker_exec(["sh", "-c", f"cat > {path}"], input_text=term)
    if proc.returncode != 0:
        raise DevnetError(f"could not write term: {proc.stderr.strip()}")
    return path


def key_name_for(secret: str) -> str:
    for name, entry in load_keys().items():
        if entry.get("secret") == secret:
            return name
    raise DevnetError("the signing secret is not in the key file; remote deploys need a named key")


def deploy(term: str, secret: str, phlo_limit: int = PHLO_LIMIT,
           phlo_price: int = PHLO_PRICE, valid_after: int | None = None) -> str:
    if REMOTE:
        name = key_name_for(secret)
        local = Path(f"/tmp/rgen-{uuid.uuid4().hex}.rho")
        local.write_text(term)
        op = f"suite-{uuid.uuid4().hex[:20]}"
        command = [
            str(CLI), "--node", NODE, "--keys", str(keys_path()), "--key", name,
            "--shard", SHARD, "--phlo-limit", str(phlo_limit),
            "--phlo-price", str(phlo_price), "--manifest", str(MANIFEST),
            "deploy", str(local), "--op", op, "--op-cache", str(OPS),
            "--allow-live", "--json",
        ]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=900)
        if proc.returncode != 0:
            raise DevnetError(f"remote deploy failed: {proc.stderr.strip() or proc.stdout.strip()}")
        try:
            receipt = json.loads(proc.stdout)
        except ValueError as error:
            raise DevnetError(f"remote deploy returned non-JSON: {proc.stdout[:1000]}") from error
        if receipt.get("status") != "processedWithSuccess":
            raise DevnetError(f"remote deploy status {receipt.get('status')}: {receipt}")
        return receipt["deployId"]
    vabn = height() if valid_after is None else valid_after
    path = write_term(term)
    proc = docker_exec([
        "rnode", "--grpc-host", "localhost", "deploy",
        "--phlo-limit", str(phlo_limit), "--phlo-price", str(phlo_price),
        "--private-key", secret, "--shard-id", SHARD,
        "--valid-after-block-number", str(vabn), path,
    ])
    out = (proc.stdout or "") + (proc.stderr or "")
    match = DEPLOY_RE.search(out)
    if not match:
        clean = out.split("___ Begin jemalloc statistics ___")[0].strip()
        raise DevnetError(f"deploy failed (rc={proc.returncode}):\n{clean[:3000]}")
    return match.group(1)


def deploy_status(deploy_id: str) -> dict:
    return http_json("GET", f"{NODE}/api/v1/deploy-status/{deploy_id}")


def _variant(doc: dict) -> tuple[str, dict]:
    for key, value in doc.items():
        if key.lower() in ("processedwithsuccess", "processedwitherror", "notprocessed"):
            return key.lower(), value
    return "unknown", {}


def wait_processed(deploy_id: str, timeout: float = 180.0) -> tuple[str, dict]:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = deploy_status(deploy_id)
        variant, payload = _variant(last)
        if variant not in ("notprocessed", "unknown"):
            return variant, payload
        time.sleep(0.5)
    raise DevnetError(f"deploy {deploy_id} not processed within {timeout}s: {last}")


def deploy_result(deploy_id: str, timeout: float = 180.0):
    variant, payload = wait_processed(deploy_id, timeout)
    if variant == "processedwithsuccess":
        return payload.get("deployResult")
    if variant == "processedwitherror":
        raise DevnetError(f"deploy errored: {payload.get('deployError')}")
    raise DevnetError(f"deploy {deploy_id}: {variant} {payload}")


def deploy_and_wait(term: str, secret: str, **kwargs):
    deploy_id = deploy(term, secret, **kwargs)
    return deploy_id, deploy_result(deploy_id)


def propose() -> dict:
    return http_json("POST", f"{ADMIN}/api/v1/propose", timeout=120.0)


def explore(term: str):
    return http_json("POST", f"{NODE}/api/v1/explore-deploy", body=term)


def faucet(address: str) -> dict:
    return http_json("POST", FAUCET_URL, body={"address": address})


def transfer_rev(source: str, target_public: str, amount: int = 1_000_000_000,
                 phlo_limit: int = 2_000_000):
    """Devnet-only top-up: move native REV from the genesis-funded deployer.

    The public faucet allows one drip per address, so a long local suite run cannot
    top an actor up through it. The devnet deployer is genesis-funded; this is the
    local equivalent of a bank account, not a testnet operation.
    """
    if REMOTE:
        raise DevnetError("native REV transfers are a local-devnet helper")
    term = (
        "new revAddress(`rho:rev:address`), revVault(`rho:rchain:revVault`), "
        "deployerId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`), "
        "aCh, vCh in { "
        f'revAddress!("fromPublicKey", "{target_public}".hexToBytes(), *aCh) | '
        "for (@addr <- aCh) { "
        f'revVault!("transfer", *deployerId, addr, {amount}, *vCh) | '
        "for (@ok <- vCh) { deployId!(ok) } } }"
    )
    return deploy_and_wait(term, secret_for(source), phlo_limit=phlo_limit)


def keys_path() -> Path:
    return Path(os.environ.get("RGEN_KEYS", _CFG.get("keys", ".devnet/keys.json")))


def load_keys() -> dict:
    path = keys_path()
    if not path.is_file():
        raise DevnetError(f"missing {path}; run `make keys`")
    return json.loads(path.read_text())


def secret_for(name: str = "deployer") -> str:
    keys = load_keys()
    if name not in keys:
        raise DevnetError(f"no key named {name} in {keys_path()}")
    return keys[name]["secret"]
