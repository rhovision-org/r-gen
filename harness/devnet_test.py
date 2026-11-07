#!/usr/bin/env python3
"""Run the local-devnet test tiers.

Tiers:

* smoke   — preflight, install, manifest verify, identity/credentials/claim.
* full    — smoke + all ten suites, red team, deploy-semantics probe, demo seed/verify,
            web tests and both Playwright journeys, static/Lean/docs gates.
* nightly — full + reinstall check and a short deploy soak. Recovery/fault injection is a
            planned follow-up and is recorded as skipped, never as a pass.

A missing or unhealthy node exits 2. A failing test exits 1. All steps and timings are
written to `deployments/devnet-test-<tier>.json`.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
MAKE = ["make", f"PY={PY}"]
RESULTS: list[dict] = []


def run(name: str, command: list[str], env: dict[str, str] | None = None,
        timeout: float = 3600.0) -> tuple[bool, str]:
    start = time.time()
    print(f"==> {name}", flush=True)
    merged = dict(os.environ)
    if env:
        merged.update(env)
    try:
        proc = subprocess.run(
            command, cwd=ROOT, env=merged, capture_output=True, text=True, timeout=timeout
        )
        rc = proc.returncode
        output = (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as error:
        rc = 124
        output = f"timeout after {timeout}s: {error}"
    seconds = round(time.time() - start, 1)
    status = "pass" if rc == 0 else "fail"
    RESULTS.append({
        "name": name,
        "command": command,
        "status": status,
        "returncode": rc,
        "seconds": seconds,
        "output_tail": "\n".join(output.strip().splitlines()[-20:]),
    })
    print(f"    {status} ({seconds}s)", flush=True)
    if rc != 0:
        for line in output.strip().splitlines()[-30:]:
            print(f"    {line}", file=sys.stderr, flush=True)
    return rc == 0, output


def make(*targets: str, env: dict[str, str] | None = None, timeout: float = 3600.0):
    return run(" ".join(targets), MAKE + list(targets), env=env, timeout=timeout)


def verify_manifest_retry() -> bool:
    """A fresh install can expose the Root a block before the manifest is readable; a
    read-only verify may need one or two retries. Failed attempts are marked retried, not
    failed, in the final report."""
    start = len(RESULTS)
    for attempt in range(3):
        ok, _ = make("devnet-verify")
        if ok:
            for step in RESULTS[start:]:
                if step.get("name") == "devnet-verify" and step.get("status") == "fail":
                    step["status"] = "retried"
            return True
        if attempt < 2:
            print("    manifest not visible yet; retrying in 3s", flush=True)
            time.sleep(3)
    return False


def check_pin(strict: bool) -> None:
    config = json.loads((ROOT / "configs" / "rholo.json").read_text())
    pinned = config["pinned_commit"]
    rholo = Path(os.environ.get("RHOLO_DIR", str(ROOT.parent / "RNodeRust"))).resolve()
    try:
        head = subprocess.run(
            ["git", "-C", str(rholo), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(rholo), "status", "--porcelain"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        RESULTS.append({"name": "pin", "status": "warn", "detail": str(error)})
        if strict:
            raise SystemExit(2)
        return
    ok = head == pinned and not dirty
    RESULTS.append({
        "name": "pin", "status": "pass" if ok else "warn",
        "pinned": pinned, "head": head, "dirty": bool(dirty),
    })
    if ok:
        print(f"pin: {head} clean")
    else:
        print(f"pin: WARNING node is {head}{' dirty' if dirty else ''}, pin is {pinned}",
              file=sys.stderr)
        if strict:
            raise SystemExit(2)


def preflight(strict_pin: bool) -> None:
    check_pin(strict_pin)
    ok, _ = make("devnet-doctor")
    if not ok:
        raise SystemExit(2)


def start_devnet(reset: bool) -> None:
    if reset:
        ok, _ = make("devnet-reset")
        if not ok:
            raise SystemExit(2)
    ok, _ = make("devnet-up")
    if not ok:
        raise SystemExit(2)
    ok, _ = make("devnet-wait")
    if not ok:
        raise SystemExit(2)


def setup() -> None:
    for target in ("client-build", "keys", "install"):
        ok, _ = make(target)
        if not ok:
            raise SystemExit(1)
    if not verify_manifest_retry():
        raise SystemExit(1)
    ok, _ = make("sync-manifest")
    if not ok:
        raise SystemExit(1)


def smoke() -> None:
    for target in ("unit-identity", "unit-credentials", "unit-claim"):
        ok, _ = make(target)
        if not ok:
            raise SystemExit(1)


def full() -> None:
    smoke()
    ok, _ = make("unit-all")
    if not ok:
        raise SystemExit(1)
    ok, _ = make("redteam", env={"RGEN_EXPECT": "fixed"})
    if not ok:
        raise SystemExit(1)
    ok, _ = make("probe-deploy-semantics")
    if not ok:
        raise SystemExit(1)
    ok, _ = make("demo-seed")
    if not ok:
        raise SystemExit(1)
    ok, _ = make("demo-verify")
    if not ok:
        raise SystemExit(1)
    ok, _ = make("sync-manifest")
    if not ok:
        raise SystemExit(1)
    if not (ROOT / "web" / "node_modules").is_dir():
        ok, _ = make("web-install")
        if not ok:
            raise SystemExit(1)
    for target in ("web-test", "web-typecheck", "web-wasm-smoke", "web-build"):
        ok, _ = make(target)
        if not ok:
            raise SystemExit(1)
    ok, _ = run("web e2e read", ["npm", "--prefix", "web", "run", "test:e2e"],
                env={"RGEN_E2E": "1"})
    if not ok:
        raise SystemExit(1)
    ok, _ = run("web e2e handshake", ["npm", "--prefix", "web", "run", "test:e2e"],
                env={"RGEN_E2E": "1", "RGEN_E2E_JOURNEY": "1"})
    if not ok:
        raise SystemExit(1)
    ok, _ = make("check")
    if not ok:
        raise SystemExit(1)
    ok, _ = make("lean-check")
    if not ok:
        raise SystemExit(1)


def nightly() -> None:
    full()
    # Reinstall on the same chain: the new Root must resolve 9/9. The old catalogue is
    # verified against the pre-reinstall manifest, because the new install creates new
    # factories/registries and cannot verify the old claims.
    import shutil  # noqa: PLC0415

    old_manifest = ROOT / ".devnet" / "manifest-before-reinstall.json"
    old_manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "deployments" / "devnet.json", old_manifest)
    ok, _ = make("install")
    if not ok:
        raise SystemExit(1)
    if not verify_manifest_retry():
        raise SystemExit(1)
    ok, _ = run("demo verify old manifest", [
        PY, "harness/demo_verify.py",
        "--catalogue", "deployments/catalogue.json",
        "--manifest", str(old_manifest),
    ])
    if not ok:
        raise SystemExit(1)
    # Short soak: height must advance and no deploy may fail.
    sys.path.insert(0, str(ROOT / "harness"))
    import actors  # noqa: E402
    import assertions  # noqa: E402

    start_height = actors.block_height()
    for index in range(20):
        assertions.one(actors.PING, key="deployer", phlo_limit=4_000_000)
    end_height = actors.block_height()
    RESULTS.append({
        "name": "soak-20-deploys",
        "status": "pass" if end_height > start_height else "fail",
        "start_height": start_height,
        "end_height": end_height,
    })
    if end_height <= start_height:
        raise SystemExit(1)
    RESULTS.append({
        "name": "recovery-fault-injection",
        "status": "skipped",
        "reason": "fault-injection recovery suite is a planned follow-up",
    })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", choices=("smoke", "full", "nightly"), default="smoke")
    parser.add_argument("--no-reset", action="store_true",
                        help="reuse the existing chain instead of resetting to genesis")
    parser.add_argument("--keep", action="store_true", help="leave the devnet running")
    parser.add_argument("--strict-pin", action="store_true",
                        help="fail when the RNodeRust checkout is not the pinned clean commit")
    parser.add_argument("--json", default=None)
    args = parser.parse_args()

    started = datetime.now(timezone.utc)
    try:
        preflight(args.strict_pin)
        start_devnet(not args.no_reset)
        setup()
        if args.tier == "smoke":
            smoke()
        elif args.tier == "full":
            full()
        else:
            nightly()
    except SystemExit as error:
        code = int(error.code) if isinstance(error.code, int) else 1
        finish(args, started, code)
        return code
    except Exception as error:  # noqa: BLE001 - the runner must record, not traceback
        RESULTS.append({"name": "runner", "status": "fail", "detail": str(error)})
        finish(args, started, 2)
        return 2
    finish(args, started, 0)
    return 0


def finish(args, started: datetime, code: int) -> None:
    out = Path(args.json) if args.json else ROOT / "deployments" / f"devnet-test-{args.tier}.json"
    payload = {
        "tier": args.tier,
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": code,
        "steps": RESULTS,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    failed = [step for step in RESULTS if step.get("status") == "fail"]
    skipped = [step for step in RESULTS if step.get("status") == "skipped"]
    print(f"devnet-test: tier={args.tier} exit={code} steps={len(RESULTS)} "
          f"fail={len(failed)} skipped={len(skipped)}", flush=True)
    print(f"devnet-test: wrote {out}", flush=True)
    if not args.keep:
        make("down")


if __name__ == "__main__":
    raise SystemExit(main())
