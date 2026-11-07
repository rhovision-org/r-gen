#!/usr/bin/env python3
"""Tie each deployed mutating arm to its manifest cell metadata.

For every `contract Name(@"arm", ...)` block in `contracts/src` that consumes a state cell
with `<-`, the arm must have a `spec/flows/core.yaml` entry with a `cell:` field equal to
the consumed state cell. If the entry declares `transition`, `authority`, or `guard_eq`,
the named Lean declaration must exist.

This is a coarse hand-encoding check, not a refinement: it catches missing metadata and
drift between the source's consumed cell and the manifest.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "spec" / "flows" / "core.yaml"
LEAN_DIR = ROOT / "spec" / "lean" / "RGen"
CONTRACT = re.compile(r'contract\s+([A-Za-z0-9_]+)\s*\(\s*@"([A-Za-z0-9_]+)"')
CONTRACT_ANY = re.compile(r'contract\s+([A-Za-z0-9_]+)\s*\(')
CALL = re.compile(r"\b([A-Za-z0-9_]+)!\(")
CELLS = {
    "rootState", "directoryState", "identityState", "issuerState", "factoryState",
    "credState", "caseState", "pState", "vpState", "claimState", "kState",
    "claimRegistryState", "vpRegistryState",
}
DECL = re.compile(r"\b(?:theorem|lemma|def)\s+([A-Za-z0-9_']+)")


def block_end(text: str, start: int) -> int | None:
    i = text.find("{", start)
    if i < 0:
        return None
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return j + 1
    return None


def parse_manifest(path: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("- "):
            if current is not None:
                entries.append(current)
            current = {}
            line = line[2:]
        if current is None or ":" not in line:
            continue
        key, value = line.split(":", 1)
        current[key.strip()] = value.strip().strip('"').strip("'")
    if current is not None:
        entries.append(current)
    return entries


def lean_decls() -> set[str]:
    names: set[str] = set()
    for path in sorted(LEAN_DIR.rglob("*.lean")):
        if ".lake" in path.parts:
            continue
        names.update(DECL.findall(path.read_text()))
    return names


def direct_consumed(block: str) -> set[str]:
    return {cell for cell in CELLS
            if re.search(rf"(?<!<)<-\s*{cell}\b", block)}


def helper_blocks(text: str) -> dict[str, str]:
    """Collect non-arm contract bodies so an arm's consumed cell can be found through
    a flat helper chain (for example KAsset.nest -> nestGate -> nestPhase3 -> kState)."""
    out: dict[str, str] = {}
    for match in CONTRACT_ANY.finditer(text):
        end = block_end(text, match.start())
        if end is None:
            continue
        paren = text.find("(", match.start())
        if text[paren + 1:].lstrip().startswith('@"'):
            continue
        block = text[match.start():end]
        name = match.group(1)
        out[name] = out.get(name, "") + block
    return out


def transitive_consumed(name: str, helpers: dict[str, str],
                        visiting: set[str] | None = None) -> set[str]:
    if visiting is None:
        visiting = set()
    if name in visiting or name not in helpers:
        return set()
    visiting.add(name)
    block = helpers[name]
    cells = direct_consumed(block)
    for call in CALL.findall(block):
        cells |= transitive_consumed(call, helpers, visiting)
    return cells


def main() -> int:
    entries = parse_manifest(MANIFEST)
    index = {(e.get("file"), e.get("contract"), e.get("arm")): e for e in entries}
    decls = lean_decls()
    errors: list[str] = []
    seen: set[tuple[str, str, str]] = set()

    for path in sorted((ROOT / "contracts" / "src").rglob("*.rho")):
        text = path.read_text()
        rel = str(path.relative_to(ROOT))
        helpers = helper_blocks(text)
        for match in CONTRACT.finditer(text):
            end = block_end(text, match.start())
            if end is None:
                errors.append(f"{rel}: unterminated {match.group(1)}")
                continue
            block = text[match.start():end]
            consumed = direct_consumed(block)
            if not consumed:
                for call in CALL.findall(block):
                    consumed |= transitive_consumed(call, helpers)
            if not consumed:
                continue
            key = (rel, match.group(1), match.group(2))
            seen.add(key)
            entry = index.get(key)
            if entry is None:
                errors.append(f"{rel}: {match.group(1)} {match.group(2)} missing manifest entry")
                continue
            cell = entry.get("cell")
            if not cell:
                errors.append(f"{rel}: {match.group(1)} {match.group(2)} missing cell")
            elif cell not in consumed:
                errors.append(
                    f"{rel}: {match.group(1)} {match.group(2)} consumes {consumed}, "
                    f"manifest says {cell}")
            for field in ("transition", "authority", "guard_eq"):
                value = entry.get(field)
                if value and value != "-":
                    short = value.rsplit(".", 1)[-1]
                    if short not in decls:
                        errors.append(f"{key}: {field} {value} not found")

    for entry in entries:
        key = (entry.get("file"), entry.get("contract"), entry.get("arm"))
        if entry.get("cell") and key not in seen:
            errors.append(f"manifest cell for non-mutating arm {key}")

    if errors:
        for error in errors:
            print(f"check_arm_guards: {error}", file=sys.stderr)
        print(f"check_arm_guards: {len(errors)} error(s)", file=sys.stderr)
        return 1

    print(f"check_arm_guards: {len(seen)} mutating arm(s) tied to a consumed cell")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
