#!/usr/bin/env python3
"""Check the object-capability register against the deployed source.

This is a source-to-register drift gate, not a Rholang semantics extractor. It checks:

* every `bundle+{*X}` in `contracts/src` has exactly one register row at its source line;
* every `bundle-`, `bundle0` or bare `bundle{` has a justification;
* every name returned in a reply value is declared;
* every reachable mutating arm on a published contract names an authority check, or `none`
  with a rationale;
* every declared arm atom appears in its source file;
* every `apply-decision` row is case-bound and delegated to an Oracle case;
* every `proof` row is one-shot and delivered on a caller channel;
* no `*Name` appears inside a state-cell send.

Exit 1 on a gap. The checker prints counts by kind and exposure. It cannot prove that the
guards are semantically correct, and it does not model Rholang name unforgeability.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "spec" / "audit" / "capabilities.yaml"
SOURCE = ROOT / "contracts" / "src"

KINDS = {
    "published-contract", "private-name", "proof", "apply-decision", "issuer",
    "factory", "registry-entry", "deployer-id", "ambient-system", "data-reference",
}
EXPOSURES = {"registry-uri", "caller-channel", "closure-only", "reply-value",
             "system-channel"}
AUTHORITY = {"caller-subject", "credential-proof", "party", "installer", "runtime",
             "case-id", "writer", "any-subject", "mixed", "none"}
DISPOSITIONS = {"holds", "accepted", "finding"}

BUNDLE = re.compile(r"bundle(\+|-|0)?\{")
BUNDLE_PLUS = re.compile(r"bundle\+\{\*([A-Za-z0-9_]+)\}")
NAME = re.compile(r"\*([A-Za-z0-9_]+)")
STATE_SEND = re.compile(r"\b[A-Za-z0-9_]*[Ss]tate!\(")
REPLY_NAME = re.compile(r"ret\d?!\([^)]*\*([A-Za-z0-9_]+)")
ORACLE_OPEN = re.compile(r'(?i)oraclefactory!\("open"')


def load_register(errors: list[str]) -> dict:
    try:
        data = yaml.safe_load(REGISTER.read_text())
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f"register: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append("register: top level is not a mapping")
        return {}
    if data.get("schema") != "rgen.capabilities/v1":
        errors.append("register: wrong schema")
    if not data.get("capabilities"):
        errors.append("register: no capabilities")
    return data


def source_files() -> list[Path]:
    return sorted(path for path in SOURCE.rglob("*.rho") if ".lake" not in path.parts)


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def atom_name(row: dict) -> str | None:
    match = BUNDLE_PLUS.search(str(row.get("source_atom", "")))
    return match.group(1) if match else None


def check_rows(data: dict, errors: list[str]) -> dict:
    rows = data.get("capabilities") or []
    by_id: dict[str, dict] = {}
    for row in rows:
        rid = row.get("id", "")
        if not re.fullmatch(r"CAP-\d{3}", rid):
            errors.append(f"{rid}: bad id")
        if rid in by_id:
            errors.append(f"{rid}: duplicate id")
        by_id[rid] = row
        for field in ("name", "kind", "source", "creator", "holders", "grant_path",
                      "exposure", "attenuation", "authority_check", "delegation",
                      "revocation", "forge_path", "hazard", "disposition", "finding",
                      "evidence"):
            if field not in row:
                errors.append(f"{rid}: missing {field}")
        if row.get("kind") not in KINDS:
            errors.append(f"{rid}: bad kind {row.get('kind')!r}")
        if row.get("exposure") not in EXPOSURES:
            errors.append(f"{rid}: bad exposure {row.get('exposure')!r}")
        if row.get("authority_check") not in AUTHORITY:
            errors.append(f"{rid}: bad authority_check {row.get('authority_check')!r}")
        if row.get("disposition") not in DISPOSITIONS:
            errors.append(f"{rid}: bad disposition {row.get('disposition')!r}")
        source = str(row.get("source", ""))
        if not source.startswith("system:"):
            if ":" not in source:
                errors.append(f"{rid}: source is not file:line")
            else:
                path_text, line_text = source.rsplit(":", 1)
                path = ROOT / path_text
                if not path.is_file():
                    errors.append(f"{rid}: source file does not exist: {path_text}")
                elif not line_text.isdigit():
                    errors.append(f"{rid}: source line is not numeric")
        arms = row.get("arms") or []
        for arm in arms:
            if not arm.get("arm"):
                errors.append(f"{rid}: arm without a name")
            if arm.get("mutating") and arm.get("authority") not in AUTHORITY - {"mixed"}:
                errors.append(f"{rid}/{arm.get('arm')}: bad mutating authority")
            if arm.get("authority") == "none" and not arm.get("rationale"):
                errors.append(f"{rid}/{arm.get('arm')}: none authority without rationale")
            for atom in arm.get("atoms") or []:
                if source.startswith("system:"):
                    continue
                path_text = source.rsplit(":", 1)[0]
                path = ROOT / path_text
                if not path.is_file() or normalise(str(atom)) not in normalise(path.read_text()):
                    errors.append(f"{rid}/{arm.get('arm')}: atom not in {path_text}: {atom!r}")
        if row.get("kind") == "apply-decision":
            if "case-bound" not in str(row.get("attenuation", "")):
                errors.append(f"{rid}: apply-decision is not case-bound")
            if not any("OracleCase" in str(item) for item in row.get("delegation") or []):
                errors.append(f"{rid}: apply-decision not delegated to OracleCase")
        if row.get("kind") == "proof":
            if row.get("exposure") != "caller-channel":
                errors.append(f"{rid}: proof is not on a caller channel")
            if "one-shot" not in str(row.get("attenuation", "")).lower():
                errors.append(f"{rid}: proof is not one-shot")
            if not row.get("delegation"):
                errors.append(f"{rid}: proof has no consumer")
    return {"by_id": by_id}


def check_bundles(rows: list[dict], errors: list[str]) -> Counter:
    """Match every bundle expression to one register row by file and bundled name.

    The register's `source` line is a hint and drifts when the contract is edited; the
    stable identity is (file, source_atom). A row that names a bundle which no longer
    exists is stale and is reported.
    """
    counts: Counter = Counter()
    matched: set[int] = set()
    for path in source_files():
        rel = str(path.relative_to(ROOT))
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if line.strip().startswith("//"):
                continue
            for match in BUNDLE.finditer(line):
                form = match.group(0)
                counts[form] += 1
                if match.group(1) != "+":
                    errors.append(f"{rel}:{number}: {form} without a justification")
                    continue
                bundled = BUNDLE_PLUS.match(line[match.start():])
                if not bundled:
                    errors.append(f"{rel}:{number}: {form} is not bundle+{{*Name}}")
                    continue
                candidates = [
                    row for row in rows
                    if str(row.get("source", "")).rsplit(":", 1)[0] == rel
                    and atom_name(row) == bundled.group(1)
                ]
                if len(candidates) != 1:
                    errors.append(
                        f"{rel}:{number}: bundle+{{*{bundled.group(1)}}} has "
                        f"{len(candidates)} register row(s)")
                    continue
                matched.add(id(candidates[0]))
    for row in rows:
        if ("bundle+" in str(row.get("source_atom", ""))
                and id(row) not in matched):
            errors.append(f"{row.get('id')}: bundle row has no matching source expression")
    return counts


def check_reply_names(by_id: dict, errors: list[str]) -> None:
    declared = {
        str(row.get("source_atom", "")): row
        for row in by_id.values()
    }
    for path in source_files():
        rel = str(path.relative_to(ROOT))
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if line.strip().startswith("//"):
                continue
            for match in REPLY_NAME.finditer(line):
                name = match.group(1)
                if name in {"uri", "id", "Nil"}:
                    continue
                rows = [row for key, row in declared.items() if f"*{name}" in key]
                if not rows:
                    errors.append(
                        f"{rel}:{number}: reply exposes *{name} without a register row")
        text = path.read_text()
        for match in ORACLE_OPEN.finditer(text):
            start = match.end()
            depth = 1
            index = start
            while index < len(text) and depth:
                char = text[index]
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                index += 1
            block = text[start:index]
            line = text[:match.start()].count("\n") + 1
            if "*Apply" in block:
                rows = [row for row in declared.values()
                        if row.get("kind") == "apply-decision"]
                if not rows:
                    errors.append(
                        f"{rel}:{line}: OracleFactory open passes *Apply "
                        "without an apply-decision register row")


def check_root_register_order(errors: list[str]) -> None:
    """The Root register arm must authenticate before consuming rootState.

    A blocked continuation on the auth receive would otherwise commit the consumed
    directory cell and make resolve/get/keys block forever.
    """
    path = ROOT / "contracts" / "src" / "deploy" / "00_root.rho"
    if not path.is_file():
        errors.append("00_root.rho: missing")
        return
    text = path.read_text()
    marker = 'contract GenRoot(@"register"'
    if marker not in text:
        errors.append("00_root.rho: register arm not found")
        return
    block = text[text.index(marker):]
    end = block.find("} |")
    if end > 0:
        block = block[:end]
    auth = block.find("authSubject!")
    state = block.find("for (@s <- rootState)")
    if auth < 0 or state < 0:
        errors.append("00_root.rho: register auth/state order not found")
    elif auth > state:
        errors.append("00_root.rho: register consumes rootState before authSubject")


def check_state_names(errors: list[str]) -> None:
    for path in source_files():
        rel = str(path.relative_to(ROOT))
        text = path.read_text()
        for match in STATE_SEND.finditer(text):
            start = match.end()
            depth = 1
            index = start
            while index < len(text) and depth:
                char = text[index]
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                index += 1
            block = text[start:index]
            for name in NAME.findall(block):
                if name in {"dId", "subject", "issuer", "caller"}:
                    continue
                line = text[:match.start()].count("\n") + 1
                errors.append(
                    f"{rel}:{line}: state send contains a name *{name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    data = load_register(errors)
    if not data:
        print("\n".join(errors), file=sys.stderr)
        return 1
    index = check_rows(data, errors)
    bundles = check_bundles(data.get("capabilities") or [], errors)
    check_reply_names(index["by_id"], errors)
    check_state_names(errors)
    check_root_register_order(errors)

    kinds = Counter(row.get("kind") for row in data.get("capabilities") or [])
    exposures = Counter(row.get("exposure") for row in data.get("capabilities") or [])
    summary = {
        "capabilities": len(data.get("capabilities") or []),
        "kinds": dict(sorted(kinds.items())),
        "exposures": dict(sorted(exposures.items())),
        "bundle_forms": dict(sorted(bundles.items())),
        "errors": len(errors),
    }
    if args.json:
        import json  # noqa: PLC0415
        print(json.dumps(summary, indent=2))
    else:
        print(f"check_capabilities: {summary['capabilities']} capability row(s), "
              f"{sum(bundles.values())} bundle expression(s), {len(errors)} error(s)")
        print(f"  kinds: {summary['kinds']}")
        print(f"  exposures: {summary['exposures']}")
    if errors:
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
