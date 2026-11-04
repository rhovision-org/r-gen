#!/usr/bin/env python3
"""Render and install the seven-term core on the public testnet through the Rust signer.

Every deploy is signed by `rgen-cli deploy` with a write-ahead op cache. A retry reuses
the exact signed body; a merge-rejected step is not retried blindly. The installer stops
on a refusal, a deploy error, or an unknown outcome and leaves the cache for inspection.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from minify_rho import minify  # noqa: E402

ORDER = [
    "00_root.rho",
    "10_identity.rho",
    "11_credentials.rho",
    "30_oracle.rho",
    "40_provenance.rho",
    "22_value.rho",
    "20_claim.rho",
]
PLACEHOLDERS = (
    "__ROOT_URI__",
    "__IDENTITY_DIRECTORY_URI__",
    "__CREDENTIAL_FACTORY_URI__",
    "__ORACLE_FACTORY_URI__",
    "__VALUE_PROPOSITION_FACTORY_URI__",
)
LIVE_HINTS = ("rhobot.net", "164.90.140.144", "167.99.43.214")


def render(name: str, values: dict[str, str]) -> str:
    source = ROOT / "contracts" / "build" / "deploy" / name
    if not source.is_file():
        raise SystemExit(f"install-testnet: missing {source}; run `make build`")
    text = source.read_text()
    for key, value in values.items():
        text = text.replace(key, value)
    leftover = [key for key in PLACEHOLDERS if key in text]
    if leftover:
        raise SystemExit(f"install-testnet: {name} has unresolved placeholders {leftover}")
    return minify(text)


def find_uri(value: object) -> str | None:
    if isinstance(value, str):
        return value if value.startswith("rho:id:") else None
    if isinstance(value, list):
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


def uri_map(value: object, out: dict[str, str] | None = None) -> dict[str, str]:
    out = {} if out is None else out
    if isinstance(value, list):
        if (
            len(value) == 2
            and isinstance(value[0], str)
            and isinstance(value[1], str)
            and value[1].startswith("rho:id:")
        ):
            out[value[0]] = value[1]
        else:
            for item in value:
                uri_map(item, out)
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str) and item.startswith("rho:id:"):
                out[key] = item
            else:
                uri_map(item, out)
    return out


def cli(args: list[str], node: str, keys: Path, shard: str, limit: int, price: int,
        manifest: Path) -> subprocess.CompletedProcess:
    command = [
        str(ROOT / "target" / "debug" / "rgen-cli"),
        "--node",
        node,
        "--keys",
        str(keys),
        "--key",
        "deployer",
        "--shard",
        shard,
        "--phlo-limit",
        str(limit),
        "--phlo-price",
        str(price),
        "--manifest",
        str(manifest),
        *args,
    ]
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", default=None)
    parser.add_argument("--keys", type=Path, default=ROOT / ".testnet" / "keys.json")
    parser.add_argument("--shard", default="/testnet")
    parser.add_argument("--phlo-limit", type=int, default=8_000_000)
    parser.add_argument("--phlo-price", type=int, default=1)
    parser.add_argument("--ops", type=Path, default=ROOT / ".testnet" / "ops")
    parser.add_argument("--manifest", type=Path, default=ROOT / "deployments" / "testnet.json")
    parser.add_argument("--state", type=Path, default=ROOT / ".testnet" / "install.json")
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    profile = json.loads((ROOT / "configs" / "testnet.json").read_text())
    node = args.node or profile["node"]
    if any(hint in node for hint in LIVE_HINTS) and not args.allow_live and not args.dry_run:
        print("install-testnet: live endpoint; pass --allow-live", file=sys.stderr)
        return 2
    if not args.keys.is_file():
        print(f"install-testnet: missing {args.keys}; run `make testnet-keys`", file=sys.stderr)
        return 3
    if not (ROOT / "target" / "debug" / "rgen-cli").is_file():
        print("install-testnet: build the CLI first: cargo build -p rgen-cli", file=sys.stderr)
        return 3

    live = any(hint in node for hint in LIVE_HINTS)
    allow = ["--allow-live"] if live else []
    values = {key: "rho:id:dryrun" for key in PLACEHOLDERS}
    state: dict[str, object] = {"networkId": profile["networkId"], "shardId": args.shard,
                                "node": node, "components": {}}
    args.ops.mkdir(parents=True, exist_ok=True)
    terms = ROOT / ".testnet" / "terms"
    terms.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temporary:
        temp_manifest = Path(temporary) / "manifest.json"
        temp_manifest.write_text(json.dumps({"root_uri": "rho:id:install", "components": {}}))

        for index, name in enumerate(ORDER, start=1):
            term = render(name, values)
            term_path = terms / name
            term_path.write_text(term)
            size = len(term.encode())
            if size > 65536:
                raise SystemExit(f"install-testnet: {name} is {size} bytes; node parses at most 65536")
            if args.dry_run:
                print(f"install-testnet: rendered {name} ({size} bytes)")
                continue

            # After the Root exists, give the CLI a manifest it can parse.
            if "root_uri" in state:
                temp_manifest.write_text(
                    json.dumps(
                        {
                            "root_uri": state["root_uri"],
                            "components": state["components"],
                        }
                    )
                )

            op = f"rgen-install-{index}-{name.replace('.rho', '')}"
            result = cli(
                [
                    "deploy",
                    str(term_path),
                    "--op",
                    op,
                    "--op-cache",
                    str(args.ops),
                    *allow,
                    "--json",
                ],
                node,
                args.keys,
                args.shard,
                args.phlo_limit,
                args.phlo_price,
                temp_manifest,
            )
            if result.returncode != 0:
                print(f"install-testnet: {name} failed: {result.stderr.strip()}", file=sys.stderr)
                print("install-testnet: the op cache was kept; reconcile before retrying", file=sys.stderr)
                return 4
            try:
                receipt = json.loads(result.stdout)
            except ValueError:
                print(f"install-testnet: {name} returned non-JSON: {result.stdout}", file=sys.stderr)
                return 4
            if receipt.get("status") != "processedWithSuccess":
                print(f"install-testnet: {name} status {receipt.get('status')}", file=sys.stderr)
                return 4
            reply = receipt.get("reply")
            if isinstance(reply, list) and reply and reply[0] is False:
                print(f"install-testnet: {name} refused: {reply}", file=sys.stderr)
                return 4
            if reply is None:
                print(f"install-testnet: {name} returned no reply", file=sys.stderr)
                return 4

            if name == "00_root.rho":
                root_uri = find_uri(reply)
                if not root_uri:
                    print(f"install-testnet: no Root URI in {reply}", file=sys.stderr)
                    return 4
                state["root_uri"] = root_uri
                state["components"]["root"] = root_uri
                values["__ROOT_URI__"] = root_uri
                print(f"install-testnet: root {root_uri}")
            else:
                found = uri_map(reply)
                state["components"].update(found)
                for component, placeholder in (
                    ("identity-directory", "__IDENTITY_DIRECTORY_URI__"),
                    ("credential-factory", "__CREDENTIAL_FACTORY_URI__"),
                    ("oracle-factory", "__ORACLE_FACTORY_URI__"),
                    ("value-proposition-factory", "__VALUE_PROPOSITION_FACTORY_URI__"),
                ):
                    if component in found:
                        values[placeholder] = found[component]
                print(f"install-testnet: {name} -> {found}")

    if args.dry_run:
        return 0

    missing = sorted(set(n for n in PLACEHOLDERS if n in values and values[n] == "rho:id:dryrun"))
    components = state["components"]
    expected = {
        "root",
        "identity-factory",
        "identity-directory",
        "issuer",
        "credential-factory",
        "oracle-factory",
        "provenance-factory",
        "value-proposition-factory",
        "claim-factory",
    }
    missing_components = sorted(expected - set(components))
    if missing or missing_components:
        print(
            f"install-testnet: incomplete install; placeholders={missing} "
            f"components={missing_components}",
            file=sys.stderr,
        )
        return 4

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps({"root_uri": state["root_uri"], "components": components}, indent=2) + "\n"
    )
    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(json.dumps(state, indent=2) + "\n")
    print(f"install-testnet: wrote {args.manifest}")

    verify = cli(
        ["manifest", "verify", "--json"],
        node,
        args.keys,
        args.shard,
        args.phlo_limit,
        args.phlo_price,
        args.manifest,
    )
    if verify.returncode != 0:
        print(f"install-testnet: verification failed: {verify.stdout}{verify.stderr}", file=sys.stderr)
        return 4
    report = json.loads(verify.stdout)
    if not report.get("ok"):
        print(f"install-testnet: manifest mismatch: {json.dumps(report.get('mismatch'))}", file=sys.stderr)
        return 4
    print("install-testnet: Root resolves all nine keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
