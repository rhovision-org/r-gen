#!/usr/bin/env python3
"""One devnet health gate for every behavioural suite and the installer.

A suite that cannot reach a healthy node must report `not run` and exit 2; it must never
crash with a traceback and must never print a pass. Run this file directly to wait for a
devnet that is still starting.
"""

from __future__ import annotations

import argparse
import sys
import time

try:
    import deploy as node
except Exception:  # pragma: no cover - import path when imported as harness.preflight
    from harness import deploy as node  # type: ignore

EXIT_NOT_RUN = 2


def devnet_ready() -> tuple[bool, str]:
    """Return (ready, reason) for the configured node."""
    try:
        status = node.http_json("GET", f"{node.NODE}/api/v1/status", timeout=10.0)
    except Exception as error:
        return False, f"unreachable at {node.NODE}: {error}"
    if "acceptsDeploys" in status and not status.get("acceptsDeploys"):
        return False, "acceptsDeploys is false"
    if "latestBlockNumber" not in status:
        return False, "status has no latestBlockNumber"
    degraded = status.get("degraded")
    if degraded == "critical":
        return False, "degraded: critical"
    return True, "ok"


def require_devnet(label: str) -> bool:
    """Print a not-run line and return False when the devnet is unhealthy."""
    ready, reason = devnet_ready()
    if ready:
        return True
    print(f"{label}: not run — {reason}", file=sys.stderr)
    return False


def wait_for_devnet(timeout: float) -> bool:
    deadline = time.time() + timeout
    last = "not checked"
    while time.time() < deadline:
        ready, last = devnet_ready()
        if ready:
            print(f"preflight: devnet ready at {node.NODE}")
            return True
        time.sleep(2.0)
    print(f"preflight: devnet not ready after {timeout:.0f}s — {last}", file=sys.stderr)
    return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", type=float, default=0.0,
                    help="seconds to wait for a healthy devnet")
    args = ap.parse_args(argv)
    if args.wait:
        return 0 if wait_for_devnet(args.wait) else EXIT_NOT_RUN
    ready, reason = devnet_ready()
    print(f"preflight: {'ready' if ready else 'not run'} — {reason}")
    return 0 if ready else EXIT_NOT_RUN


if __name__ == "__main__":
    raise SystemExit(main())
