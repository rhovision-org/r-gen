#!/usr/bin/env python3
"""Run behavioural suites and record an honest pass / fail / not-run result.

Exit codes: 0 all pass, 1 any failure, 2 any not-run and no failure. The result file is
`deployments/suite-results.json` (gitignored) and is uploaded by CI.
"""

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
    "root": "unit_root.py",
    "identity": "unit_identity.py",
    "credentials": "unit_credentials.py",
    "work": "unit_work.py",
    "kasset": "unit_kasset.py",
    "provenance": "unit_provenance.py",
    "token": "unit_token.py",
    "risk": "unit_risk.py",
    "oracle": "unit_oracle.py",
    "journey": "unit_journey.py",
    "adversarial": "unit_adversarial.py",
    "conservation": "unit_conservation.py",
    "payments": "unit_payments.py",
    "dispute": "unit_dispute.py",
}
DEFAULT = [
    "root", "identity", "credentials", "work", "kasset", "provenance",
    "token", "risk", "oracle", "journey", "adversarial", "conservation",
]


def run(name: str) -> dict:
    script = ROOT / "harness" / SUITES[name]
    started = time.time()
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0:
        status = "pass"
    elif proc.returncode == 2:
        status = "not_run"
    else:
        status = "fail"
    print(f"--- {name}: {status} ({proc.returncode}) ---")
    print(output.rstrip())
    return {
        "suite": name,
        "script": SUITES[name],
        "status": status,
        "returncode": proc.returncode,
        "seconds": round(time.time() - started, 3),
        "output": output[-4000:],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suites", default=",".join(DEFAULT),
                    help="comma-separated suite names (default: implemented suites)")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)

    if args.list:
        for name, script in SUITES.items():
            print(f"{name:14} {script}")
        return 0

    names = [name.strip() for name in args.suites.split(",") if name.strip()]
    unknown = [name for name in names if name not in SUITES]
    if unknown:
        print(f"run_suites: unknown suites {unknown}", file=sys.stderr)
        return 1

    results = [run(name) for name in names]
    payload = {
        "node": os.environ.get("RGEN_NODE", "http://localhost:40403"),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": results,
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"run_suites: wrote {RESULTS.relative_to(ROOT)}")

    if any(item["status"] == "fail" for item in results):
        return 1
    if any(item["status"] == "not_run" for item in results):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
