#!/usr/bin/env python3
"""Preflight for the local r-gen devnet.

Checks Docker, the pinned node checkout, the requested node memory, the ports the
launcher uses, and whether a node already answers. Read-only.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


def check(ok: bool, label: str, detail: str = "") -> bool:
    print(f"{'ok  ' if ok else 'FAIL'} {label}{f' — {detail}' if detail else ''}")
    return ok


def memory_mb(value: str) -> int:
    match = re.fullmatch(r"(\d+)([mMgG]?)", value.strip())
    if not match:
        raise SystemExit(f"bad --memory value: {value!r} (use 8192m or 8g)")
    amount = int(match.group(1))
    return amount if match.group(2).lower() == "m" or match.group(2) == "" else amount * 1024


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def node_status(node: str) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(f"{node.rstrip('/')}/api/v1/status", timeout=3) as response:
            document = json.loads(response.read())
        return True, f"height {document.get('latestBlockNumber', '?')}"
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as error:
        return False, str(error)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rholo-dir", type=Path, default=Path("../RNodeRust"))
    parser.add_argument("--node", default="http://localhost:40403")
    parser.add_argument("--memory", default="8g")
    args = parser.parse_args()

    ok = True
    ok &= check(shutil.which("docker") is not None, "docker is on PATH")
    launcher = args.rholo_dir / "tools" / "devnet.sh"
    ok &= check(launcher.is_file(), "devnet launcher", str(launcher))
    try:
        requested = memory_mb(args.memory)
        ok &= check(
            requested >= 6144,
            "node memory",
            f"{args.memory}; below 6g the claim-validation and nest deploys can be OOM-killed (exit 137)",
        )
    except SystemExit as error:
        ok &= check(False, "node memory", str(error))
    running, detail = node_status(args.node)
    if running:
        print(f"ok   node already answers — {detail}")
    else:
        for port in (40403, 40405):
            ok &= check(port_free(port), f"port {port} is free", "an existing devnet may hold it")
        print(f"note node does not answer yet ({detail})")
    if shutil.which("wasm-pack") is None:
        print("warn wasm-pack is not on PATH; the web app cannot build its WASM module")
    if shutil.which("npm") is None:
        print("warn npm is not on PATH; the web app cannot build")
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())
