#!/usr/bin/env python3
"""Prepare a devnet key file for the r-gen core.

The rholo devnet bakes in one funded deployer key. This tool writes that deployer plus fresh
secp256k1 keys for the behavioural actors. The REV address derivation matches
`rholo/rholang/src/util/rev_address.rs`:
    eth = keccak256(uncompressed_pubkey[1:])[-20:]
    payload = 0x00000000 || keccak256(eth)
    address = base58(payload || blake2b256(payload)[:4])
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from coincurve import PrivateKey
from Crypto.Hash import keccak

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
DEPLOYER_KEY = "a68a6e6cca30f81bd24a719f3145d20e8424bd7b396309b0708a16c7d8000b76"

ACTORS = [
    "alice", "bob", "carol", "dave", "erin", "frank", "mallory",
    "ida", "idb", "wa", "wb", "ka", "kb", "kc", "ta", "tb", "tc", "pa",
    "admin1", "admin2", "admin3",
]


def b58encode(raw: bytes) -> str:
    n = int.from_bytes(raw, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = ALPHABET[r] + out
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + out


def keccak256(data: bytes) -> bytes:
    h = keccak.new(digest_bits=256)
    h.update(data)
    return h.digest()


def public_key(secret_hex: str) -> bytes:
    return PrivateKey(bytes.fromhex(secret_hex)).public_key.format(compressed=True)


def rev_address(secret_hex: str) -> str:
    pub65 = PrivateKey(bytes.fromhex(secret_hex)).public_key.format(compressed=False)
    eth = keccak256(pub65[1:])[-20:]
    key_hash = keccak256(eth)
    payload = b"\x00\x00\x00\x00" + key_hash
    checksum = hashlib.blake2b(payload, digest_size=32).digest()[:4]
    return b58encode(payload + checksum)


def record(name: str, secret: str) -> dict:
    return {
        "name": name,
        "secret": secret,
        "public": public_key(secret).hex(),
        "address": rev_address(secret),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".devnet/keys.json")
    ap.add_argument("--from-path", default=None,
                    help="optional existing keys file; its deployer is reused")
    args = ap.parse_args(argv)

    keys = {}
    if args.from_path and Path(args.from_path).is_file():
        keys = json.loads(Path(args.from_path).read_text())

    if "deployer" not in keys:
        keys["deployer"] = record("deployer", DEPLOYER_KEY)

    for name in ACTORS:
        if name not in keys:
            keys[name] = record(name, os.urandom(32).hex())

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(keys, indent=2) + "\n")
    print(f"keygen: wrote {out} ({len(keys)} keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
