#!/usr/bin/env python3
"""Fund testnet keys from the public faucet, one drip per address.

The faucet pays 0.3 REV once per address. A drip is a deploy: wait for the native
balance to move before declaring success. Never retry a drip blindly; check the balance
first, because an already-funded address is a successful outcome.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = json.loads((ROOT / "configs" / "testnet.json").read_text())
LIVE_HINTS = ("rhobot.net", "164.90.140.144", "167.99.43.214")
BASE = 100_000_000


def post(url: str, body: dict) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def explore(node: str, term: str) -> list:
    request = urllib.request.Request(
        f"{node.rstrip('/')}/api/v1/explore-deploy",
        data=json.dumps(term).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    last: Exception | None = None
    for _ in range(6):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read()).get("expr", [])
        except urllib.error.HTTPError as error:
            if error.code not in (429, 502, 503, 504):
                raise
            last = error
            retry_after = error.headers.get("Retry-After") if error.headers else None
            time.sleep(float(retry_after) if retry_after else 5)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last = error
            time.sleep(3)
    raise RuntimeError(f"explore-deploy did not answer after retries: {last}")


def as_int(expr: object) -> int | None:
    if not isinstance(expr, dict):
        return None
    if "ExprInt" in expr:
        return int(expr["ExprInt"]["data"])
    if "ExprTuple" in expr:
        for item in expr["ExprTuple"]["data"]:
            value = as_int(item)
            if value is not None:
                return value
    return None


def balance(node: str, address: str) -> int:
    term = (
        "new reply, revVault(`rho:rchain:revVault`), ch in { "
        f'revVault!("getBalance", "{address}", *ch) | '
        "for (@b <- ch) { reply!(b) } }"
    )
    expr = explore(node, term)
    for item in expr:
        value = as_int(item)
        if value is not None:
            return value
    return 0


def wait_for_balance(node: str, address: str, minimum: int, timeout: int = 90) -> int:
    deadline = time.time() + timeout
    last = 0
    while time.time() < deadline:
        last = balance(node, address)
        if last >= minimum:
            return last
        time.sleep(2)
    return last


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", default=PROFILE["node"])
    parser.add_argument("--keys", type=Path, default=ROOT / ".testnet" / "keys.json")
    parser.add_argument("--target", default="deployer", help="deployer, all, or comma-separated names")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--out", type=Path, default=ROOT / ".testnet" / "funding.json")
    args = parser.parse_args()

    if any(hint in args.node for hint in LIVE_HINTS) and not args.allow_live:
        print("testnet-fund: live endpoint; pass --allow-live", file=sys.stderr)
        return 2
    if not args.keys.is_file():
        print(f"testnet-fund: missing {args.keys}; run `make testnet-keys`", file=sys.stderr)
        return 3
    keys = json.loads(args.keys.read_text())
    names = (
        list(keys)
        if args.target == "all"
        else [name.strip() for name in args.target.split(",") if name.strip()]
    )
    for name in names:
        if name not in keys:
            print(f"testnet-fund: no key named {name}", file=sys.stderr)
            return 3

    report = {"node": args.node, "faucet": PROFILE["faucetUrl"], "accounts": {}}
    for name in names:
        address = keys[name]["address"]
        before = balance(args.node, address)
        if args.plan:
            report["accounts"][name] = {
                "address": address,
                "balance": before,
                "balanceRev": before / BASE,
            }
            print(f"plan {name:10s} {address} {before / BASE:.8f} REV")
            continue
        if before >= int(PROFILE["phloLimit"]):
            print(f"fund {name:10s} already funded ({before / BASE:.8f} REV)")
            report["accounts"][name] = {"address": address, "balance": before, "funded": False}
            continue
        status, body = post(PROFILE["faucetUrl"], {"address": address})
        if status == 400 and ("already" in body.lower() or "funded" in body.lower()):
            print(f"fund {name:10s} faucet says already funded; checking balance")
        elif status == 429:
            print("testnet-fund: faucet rate limited; wait and re-run", file=sys.stderr)
            return 4
        elif status >= 400:
            print(f"testnet-fund: faucet {status}: {body}", file=sys.stderr)
            return 4
        after = wait_for_balance(args.node, address, int(PROFILE["phloLimit"]))
        if after <= before:
            print(
                f"testnet-fund: {name} balance did not move ({after}); "
                "do not retry until the deploy is reconciled",
                file=sys.stderr,
            )
            return 4
        print(f"fund {name:10s} {before / BASE:.8f} -> {after / BASE:.8f} REV")
        report["accounts"][name] = {"address": address, "before": before, "after": after, "funded": True}

    if not args.plan:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
        print(f"testnet-fund: wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
