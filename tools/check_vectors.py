#!/usr/bin/env python3
"""Recompute risk and mint arithmetic from spec/vectors."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VECTORS = ROOT / "spec" / "vectors"


def risk_class(score: int) -> str:
    if score <= 20:
        return "low"
    if score <= 45:
        return "medium"
    if score <= 70:
        return "high"
    return "extreme"


def main() -> int:
    errors = []
    count = 0
    for path in sorted(VECTORS.glob("*.json")):
        data = json.loads(path.read_text())
        for item in data.get("risk", []):
            count += 1
            score = item["severity"] * item["probability"] * item["exposure"]
            if score != item["score"]:
                errors.append(f"{path.name}: risk {item} expected {score}")
            if risk_class(score) != item["class"]:
                errors.append(f"{path.name}: class {item} expected {risk_class(score)}")
        for item in data.get("mint", []):
            count += 1
            quality = item["quality"]
            pct = sum(quality.values()) * 100 // 20
            if item.get("verdict") == "partial":
                pct = pct * 5000 // 10000
            total = item["unitMint"] * pct // 100
            claimant = total * 5000 // 10000
            validator = (total - claimant) * item["repBps"] // 10000
            if (claimant, validator) != (item["claimant"], item["validator"]):
                errors.append(
                    f"{path.name}: mint {item} expected ({claimant}, {validator})")
    if errors:
        for error in errors:
            print(f"check-vectors: {error}", file=sys.stderr)
        return 1
    print(f"check-vectors: {count} vector(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
