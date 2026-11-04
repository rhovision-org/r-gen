#!/usr/bin/env python3
"""Check paper citations and markdown links in the book.

Every `@key p.N` in a core contract `// Paper:` header must appear in a primitive page and
in the paper-to-code matrix; every relative Markdown link in `docs/src` must resolve.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs" / "src"
PRIMITIVES = DOCS / "primitives"
MATRIX = DOCS / "reference" / "paper-to-code.md"
CITE = re.compile(r"@([a-z][a-z0-9]+) p\.(\d+)")
LINK = re.compile(r"\]\(([^)#]+\.md)(?:#[^)]*)?\)")
PAPER = re.compile(r"^//\s*Paper:.*$", re.M)


def core_citations() -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for path in sorted((ROOT / "contracts" / "src").rglob("*.rho")):
        for line in PAPER.findall(path.read_text()):
            for key, page in CITE.findall(line):
                found.add((key, page))
    return found


def main() -> int:
    errors: list[str] = []
    citations = core_citations()
    primitive_text = "\n".join(p.read_text() for p in sorted(PRIMITIVES.glob("*.md")))
    matrix_text = MATRIX.read_text() if MATRIX.is_file() else ""
    if not matrix_text:
        errors.append(f"missing {MATRIX.relative_to(ROOT)}")

    for key, page in sorted(citations):
        needle = f"@{key} p.{page}"
        if needle not in primitive_text:
            errors.append(f"{needle} is not in any primitive page")
        if needle not in matrix_text:
            errors.append(f"{needle} is not in paper-to-code.md")

    for path in sorted(DOCS.rglob("*.md")):
        text = path.read_text()
        for target in LINK.findall(text):
            if target.startswith(("http://", "https://")):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.is_file():
                errors.append(
                    f"{path.relative_to(ROOT)}: broken link {target}")

    if errors:
        for error in errors:
            print(f"check_docs_links: {error}", file=sys.stderr)
        print(f"check_docs_links: {len(errors)} error(s)", file=sys.stderr)
        return 1

    print(f"check_docs_links: {len(citations)} code citation(s), "
          f"{len(list(DOCS.rglob('*.md')))} page(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
