#!/usr/bin/env python3
"""Prepare the devnet key file for r-share.

The rholo devnet funds one baked-in deployer key and r-cash's setup writes admin keys.
This tool reuses that file; it never embeds private key material in the repository.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))
from rcash_paths import keys_path  # noqa: E402

DEFAULT_SOURCE = keys_path()

# The devnet ships one funded deployer and r-cash's test keys. Give the behavioural suites
# stable actor names by aliasing distinct existing keys; no new key material is invented.
ALIASES = {
    "alice": "business",
    "bob": "key12",
    "carol": "key13",
    "dave": "key14",
    "erin": "key15",
    "frank": "key16",
    "mallory": "key17",
    "ida": "reporter1",
    "idb": "reporter2",
    "wa": "reporter3",
    "wb": "sender",
    "ka": "recipient",
    "kb": "sponsor",
    "kc": "ramp",
    "ta": "key18",
    "tb": "key19",
    "tc": "key20",
    "pa": "key21",
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".devnet/keys.json")
    ap.add_argument("--from-path", default=str(DEFAULT_SOURCE),
                    help="reuse an existing devnet keys file (default: r-cash's)")
    args = ap.parse_args(argv)

    source = Path(args.from_path)
    if not source.is_file():
        print(f"keygen: missing {source}", file=sys.stderr)
        print("keygen: run `make rcash-keys` first (or set RCASH_DIR)", file=sys.stderr)
        return 1

    data = json.loads(source.read_text())
    if "deployer" not in data:
        print(f"keygen: {source} has no deployer key", file=sys.stderr)
        return 1
    missing = [name for name in ("admin1", "admin2", "admin3") if name not in data]
    if missing:
        print(f"keygen: warning: {source} has no distinct {missing}; "
              "install will require --dev-single-key", file=sys.stderr)

    for actor, source_name in ALIASES.items():
        if actor not in data and source_name in data:
            data[actor] = data[source_name]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2) + "\n")
    print(f"keygen: wrote {out} ({len(data)} keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
