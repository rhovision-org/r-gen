#!/usr/bin/env python3
"""Run the Pareto-core behavioural suites and write an honest result file."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "deployments" / "suite-results.json"
SUITES = {
    "identity": "unit_identity.py",
    "credentials": "unit_credentials.py",
    "claim": "unit_claim.py",
    "kasset": "unit_kasset.py",
    "value": "unit_value.py",
    "oracle": "unit_oracle.py",
    "provenance": "unit_provenance.py",
    "integration": "integration_core.py",
    "core": "unit_core.py",
    "race": "concurrency_core.py",
    "install": "unit_install.py",
    "wiring": "unit_wiring.py",
    "azoth": "unit_azoth.py",
}
DEFAULT = ["identity", "credentials", "claim", "kasset", "value", "oracle",
           "provenance", "integration", "core", "race", "azoth"]


def run(name: str) -> dict:
    script = ROOT / "harness" / SUITES[name]
    started = time.time()
    proc = subprocess.run([sys.executable, str(script)], cwd=ROOT,
                          text=True, capture_output=True)
    output = (proc.stdout or "") + (proc.stderr or "")
    status = "pass" if proc.returncode == 0 else ("not_run" if proc.returncode == 2 else "fail")
    print(f"--- {name}: {status} ({proc.returncode}) ---")
    print(output.rstrip())
    return {"suite": name, "script": SUITES[name], "status": status,
            "returncode": proc.returncode,
            "seconds": round(time.time() - started, 3),
            "output": output[-4000:]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suites", default=",".join(DEFAULT))
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)
    if args.list:
        for name, script in SUITES.items():
            print(f"{name:8} {script}")
        return 0
    names = [n.strip() for n in args.suites.split(",") if n.strip()]
    unknown = [n for n in names if n not in SUITES]
    if unknown:
        print(f"run_core_suites: unknown suites {unknown}", file=sys.stderr)
        return 1
    results = [run(n) for n in names]
    payload = {
        "node": os.environ.get("RGEN_NODE", "http://localhost:40403"),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": results,
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"run_core_suites: wrote {RESULTS.relative_to(ROOT)}")
    if any(r["status"] == "fail" for r in results):
        return 1
    if any(r["status"] == "not_run" for r in results):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
