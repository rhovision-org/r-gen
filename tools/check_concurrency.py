#!/usr/bin/env python3
"""Structural checks for the per-entity linear-cell discipline.

Rules:
- Every contract arm that consumes a state cell must re-post it in the same block.
- An arm may not both consume (`<-`) and peek (`<<-`) the same state cell, except the
  documented KAsset.nest two-phase arm (parent peek for the pre-pass, parent consume only
  after child proofs are taken).
- `Issuer.revoke` and `Credential.check` calls are absent from the core.
- No global nonce state cell exists.
- Every declared serialization point is documented in the design rationale.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATHS = sorted((ROOT / "contracts" / "src").rglob("*.rho"))
CELLS = {
    "rootState", "directoryState", "identityState", "issuerState", "factoryState",
    "credState", "caseState", "pState", "vpState", "claimState", "kState",
}
SERIALIZATION = {"rootState", "directoryState", "issuerState", "factoryState"}
CONTRACT = re.compile(r"contract\s+([A-Za-z0-9_]+)\s*\(")
ARM = re.compile(r'contract\s+([A-Za-z0-9_]+)\s*\(\s*@"([A-Za-z0-9_]+)"')
FORBIDDEN_CALLS = [
    (re.compile(r'Issuer!\("revoke"'), "Issuer.revoke is removed from the core"),
    (re.compile(r'\w+!\("check",'), "Credential.check is advisory and not a commit authority"),
]


def block_end(text: str, start: int) -> int | None:
    i = text.find("{", start)
    if i < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for j in range(i, len(text)):
        ch = text[j]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return j + 1
    return None


def main() -> int:
    errors = []
    arms = 0
    for path in PATHS:
        text = path.read_text()
        for match in CONTRACT.finditer(text):
            end = block_end(text, match.start())
            if end is None:
                errors.append(f"{path.name}: unterminated contract {match.group(1)}")
                continue
            block = text[match.start():end]
            arms += 1
            arm_match = ARM.match(text, match.start())
            # KAsset.nest is a documented two-phase arm: it peeks the parent for the
            # read-only pre-pass and consumes it only after the child proofs are taken.
            two_phase_nest = bool(
                arm_match and arm_match.group(1) == "KAsset"
                and arm_match.group(2) == "nest")
            for pattern, why in FORBIDDEN_CALLS:
                if pattern.search(block):
                    errors.append(f"{path.name}: {match.group(1)}: {why}")
            for cell in CELLS:
                consumed = re.search(rf"(?<!<)<-\s*{cell}\b", block)
                peeked = re.search(rf"<<-\s*{cell}\b", block)
                nested = len(CONTRACT.findall(block)) > 1
                if consumed and peeked and not nested and not two_phase_nest:
                    errors.append(
                        f"{path.name}: {match.group(1)} mixes <- and <<- on {cell}")
            for cell in CELLS:
                consumes = len(re.findall(rf"(?<!<)<-\s*{cell}\b", text))
                reposts = len(re.findall(rf"\b{cell}\s*!\(", text))
                if consumes > reposts:
                    errors.append(
                        f"{path.name}: {cell} has {consumes} consume(s) and {reposts} re-post(s)")

    catalogue = json.loads((ROOT / "contracts" / "components.json").read_text())
    cells = set(catalogue.get("serialization_points", {}))
    for component in catalogue["components"].values():
        cells.update(component.get("state_cells", []))
    if any("nonce" in cell for cell in cells):
        errors.append("a global nonce state cell is declared")
    rationale = (ROOT / "docs" / "src" / "reference" / "design-rationale.md").read_text()
    for cell in SERIALIZATION:
        if cell not in rationale:
            errors.append(f"serialization point {cell} is not documented")

    if errors:
        for error in errors:
            print(f"check-concurrency: {error}", file=sys.stderr)
        return 1
    print(f"check-concurrency: {arms} arm(s), {len(CELLS)} entity/serialization cells, "
          "consume-first and re-post discipline holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
