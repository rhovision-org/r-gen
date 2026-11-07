#!/usr/bin/env python3
"""Check the decision-table bridge for the changed mutating arms.

For every arm in `spec/guards/arms.yaml`:

* every canonical source atom appears in the deployed Rholang (whitespace-normalized);
* the flow manifest still has an entry for the contract/arm;
* a named `guard_eq` theorem exists in `ArmGuards.lean`, or the arm is explicitly `owed`.

This is a drift check, not a semantics-preserving extraction. The doc says so.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
GUARDS = ROOT / "spec" / "guards" / "arms.yaml"
CORE = ROOT / "spec" / "flows" / "core.yaml"
ARM_GUARDS = ROOT / "spec" / "lean" / "RGen" / "ArmGuards.lean"


def norm(text: str) -> str:
    return " ".join(text.split())


def flow_entries() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for raw in CORE.read_text().splitlines():
        line = raw.strip()
        if line.startswith("- file:"):
            if current:
                entries.append(current)
            current = {"file": line[len("- file:"):].strip()}
        elif line.startswith("contract:"):
            current["contract"] = line[len("contract:"):].strip()
        elif line.startswith("arm:"):
            current["arm"] = line[len("arm:"):].strip()
        elif line.startswith("guard_eq:"):
            current["guard_eq"] = line[len("guard_eq:"):].strip()
    if current:
        entries.append(current)
    return entries


def main() -> int:
    config = yaml.safe_load(GUARDS.read_text()) or {}
    entries = flow_entries()
    lean_text = ARM_GUARDS.read_text()
    errors: list[str] = []
    warnings: list[str] = []
    checked = 0

    for arm in config.get("arms") or []:
        arm_id = arm.get("id", "<unnamed>")
        source = ROOT / arm["source"]
        if not source.is_file():
            errors.append(f"{arm_id}: missing source {arm['source']}")
            continue
        source_text = norm(source.read_text())
        for atom in arm.get("atoms") or []:
            if norm(atom) not in source_text:
                errors.append(f"{arm_id}: atom not found in {arm['source']}: {atom!r}")
        flow = arm.get("flow") or {}
        match = [
            e for e in entries
            if e.get("contract") == flow.get("contract") and e.get("arm") == flow.get("arm")
        ]
        if not match:
            errors.append(
                f"{arm_id}: no flow entry for {flow.get('contract')}.{flow.get('arm')}"
            )
        else:
            if not match[0].get("guard_eq") or match[0].get("guard_eq") == "-":
                warnings.append(f"{arm_id}: flow entry has no guard_eq")
        named = arm.get("guard_eq")
        if named and named != "owed":
            short = named.rsplit(".", 1)[-1]
            if f"theorem {short}" not in lean_text:
                errors.append(f"{arm_id}: guard_eq {named} is not in ArmGuards.lean")
        elif named == "owed":
            warnings.append(f"{arm_id}: guard_eq owed")
        checked += 1

    for warning in warnings:
        print(f"guard-bridge: warning: {warning}")
    if errors:
        for error in errors:
            print(f"guard-bridge: {error}", file=sys.stderr)
        return 1
    print(f"check_guard_bridge: {checked} arm(s), atoms and flow entries agree "
          f"({len(warnings)} owed/warning)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
