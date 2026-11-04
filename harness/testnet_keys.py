#!/usr/bin/env python3
"""Generate fresh testnet-only keys and optional browser keystores.

The plaintext key file is for the CLI campaign and lives under `.testnet/` with mode
0600. The encrypted keystores are what the web app imports; both are gitignored.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "target" / "debug" / "rgen-cli"
DEVNET_KEYS = ROOT / ".devnet" / "keys.json"
NAMES = ["deployer", "alice", "bob", "carol", "dave", "erin", "bank1", "bank2"]


def run(args: list[str]) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / ".testnet" / "keys.json")
    parser.add_argument("--names", default=",".join(NAMES))
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--keystores", type=Path, default=None)
    parser.add_argument("--password", default="rgen-testnet-demo")
    args = parser.parse_args()

    if args.out.exists() and not args.fresh:
        print(f"testnet-keys: {args.out} exists; pass --fresh to rotate", file=sys.stderr)
        return 3
    if not CLI.is_file():
        run(["cargo", "build", "-p", "rgen-cli"])

    names = [name.strip() for name in args.names.split(",") if name.strip()]
    run(
        [
            str(CLI),
            "keygen",
            "--out",
            str(args.out),
            "--names",
            ",".join(names),
            "--fresh",
        ]
    )
    mode = stat.S_IMODE(args.out.stat().st_mode)
    if mode & 0o077:
        raise SystemExit(f"testnet-keys: {args.out} is mode {mode:o}, expected 0600")

    keys = json.loads(args.out.read_text())
    devnet = json.loads(DEVNET_KEYS.read_text()) if DEVNET_KEYS.is_file() else {}
    devnet_public = {entry.get("public") for entry in devnet.values() if isinstance(entry, dict)}
    reused = [name for name, entry in keys.items() if entry.get("public") in devnet_public]
    if reused:
        raise SystemExit(f"testnet-keys: generated keys collide with devnet keys: {reused}")

    if args.keystores:
        args.keystores.mkdir(parents=True, exist_ok=True)
        for name in names:
            out = args.keystores / f"{name}.json"
            run(
                [
                    str(CLI),
                    "--keys",
                    str(args.out),
                    "keystore",
                    "encrypt",
                    "--name",
                    name,
                    "--password",
                    args.password,
                    "--out",
                    str(out),
                ]
            )
        print(f"testnet-keys: wrote {len(names)} keystore(s) to {args.keystores}")

    print(f"testnet-keys: wrote {args.out} with {len(keys)} key(s)")
    for name in names:
        entry = keys.get(name)
        if entry:
            print(f"  {name}\t{entry['address']}")
    if args.keystores:
        print(f"  keystore password: {args.password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
