#!/usr/bin/env python3
"""Reject unproved Lean declarations in the formal model.

The model is allowed to use Lean's core logic only. This gate rejects

* `sorry`, `admit`, and `native_decide` anywhere outside comments, and
* any declared axiom.

The axiom *audit* (`#print axioms` for every public theorem) lives in
`spec/lean/RGen/Audit.lean`; this script is the cheap static gate the CI can run
before the build.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEAN = ROOT / "spec" / "lean"
FORBIDDEN = ("sorry", "admit", "native_decide")
AXIOM_DECL = re.compile(r"^\s*(?:private\s+|protected\s+)?axiom\s+([A-Za-z_][\w.']*)", re.M)
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
AUDIT_DEPENDS = re.compile(r"^'([^']+)' depends on axioms: \[(.*)\]$")
AUDIT_NOAX = re.compile(r"^'([^']+)' does not depend on any axioms$")


def strip_comments(text: str) -> str:
    """Remove nested `/- … -/` comments and `--` line comments, keeping newlines."""
    out: list[str] = []
    i = 0
    depth = 0
    n = len(text)
    while i < n:
        if text.startswith("/-", i):
            depth += 1
            i += 2
            continue
        if depth > 0 and text.startswith("-/", i):
            depth -= 1
            i += 2
            continue
        if depth > 0:
            if text[i] == "\n":
                out.append("\n")
            i += 1
            continue
        if text.startswith("--", i):
            j = text.find("\n", i)
            if j < 0:
                break
            i = j
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def run_audit() -> int:
    """Elaborate `RGen/Audit.lean` and reject axioms outside the core set."""
    try:
        proc = subprocess.run(
            ["lake", "env", "lean", "RGen/Audit.lean"],
            cwd=LEAN, capture_output=True, text=True)
    except FileNotFoundError:
        print("check_lean: `lake` not found in PATH", file=sys.stderr)
        return 2

    output = proc.stdout + proc.stderr
    errors: list[str] = []
    checked = 0
    for line in output.splitlines():
        depends = AUDIT_DEPENDS.match(line)
        if depends:
            checked += 1
            axioms = [a.strip() for a in depends.group(2).split(",") if a.strip()]
            for axiom in axioms:
                if axiom not in ALLOWED_AXIOMS:
                    errors.append(f"{depends.group(1)}: axiom `{axiom}`")
            continue
        if AUDIT_NOAX.match(line):
            checked += 1

    if proc.returncode != 0 or "error:" in output:
        errors.append("audit elaboration failed\n" + output)
    if checked == 0:
        errors.append("audit produced no #print axioms lines")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"check_lean: {len(errors)} audit error(s)", file=sys.stderr)
        return 1
    print(f"check_lean: audit of {checked} theorem(s) is axiom-clean")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true",
                        help="elaborate RGen/Audit.lean and check #print axioms")
    args = parser.parse_args()
    if args.audit:
        return run_audit()

    if not LEAN.is_dir():
        print(f"check_lean: missing directory {LEAN.relative_to(ROOT)}", file=sys.stderr)
        return 2

    errors: list[str] = []
    paths = [p for p in sorted(LEAN.rglob("*.lean")) if ".lake" not in p.parts]
    for path in paths:
        rel = path.relative_to(ROOT)
        code = strip_comments(path.read_text())
        for token in FORBIDDEN:
            for match in re.finditer(rf"\b{token}\b", code):
                line = code.count("\n", 0, match.start()) + 1
                errors.append(f"{rel}:{line}: forbidden token `{token}`")
        for match in AXIOM_DECL.finditer(code):
            line = code.count("\n", 0, match.start()) + 1
            errors.append(f"{rel}:{line}: axiom declaration `{match.group(1)}`")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"check_lean: {len(errors)} error(s)", file=sys.stderr)
        return 1

    files = len(paths)
    print(f"check_lean: {files} file(s), no sorry/admit/native_decide/axiom")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
