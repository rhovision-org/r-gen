#!/usr/bin/env python3
"""Check paper citations in the core contracts against docs/papers/manifest.json."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "papers" / "manifest.json"
DEPLOY = ROOT / "contracts" / "src" / "deploy"
KEY = re.compile(r"@([a-z][a-z0-9]+)")
PAGE = re.compile(r"p\.(\d+)")


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    papers = {paper["key"]: paper for paper in manifest["papers"]}
    errors = []
    cited = set()

    for path in sorted(DEPLOY.glob("*.rho")):
        text = path.read_text()
        why = [line for line in text.splitlines() if line.startswith("// Why:")]
        paper_lines = [line for line in text.splitlines() if line.startswith("// Paper:")]
        if not why:
            errors.append(f"{path.name}: missing // Why:")
        if not paper_lines:
            errors.append(f"{path.name}: missing // Paper:")
            continue
        for line in paper_lines:
            if "none" in line.lower():
                continue
            for segment in line.split(";"):
                keys = KEY.findall(segment)
                if not keys:
                    continue
                key = keys[0]
                cited.add(key)
                if key not in papers:
                    errors.append(f"{path.name}: unknown citation key @{key}")
                    continue
                paper = papers[key]
                if paper.get("status") == "quarantined":
                    errors.append(f"{path.name}: quarantined paper @{key} is cited")
                extract = ROOT / "docs" / "papers" / "extract" / f"{key}.md"
                if not extract.is_file():
                    errors.append(f"{path.name}: missing extract for @{key}")
                    continue
                extract_text = extract.read_text()
                for page in PAGE.findall(segment):
                    if int(page) < 1 or int(page) > paper["pages"]:
                        errors.append(
                            f"{path.name}: @{key} p.{page} outside 1..{paper['pages']}")
                    if f"## p.{page}" not in extract_text:
                        errors.append(f"{path.name}: @{key} has no extract heading p.{page}")

    for key, paper in papers.items():
        if paper.get("status") in ("quarantined", "background"):
            continue
        if key not in cited:
            errors.append(f"@key {key} is never cited by a core term")

    for key, paper in papers.items():
        pdf = ROOT / "docs" / "papers" / paper["pdf"]
        if not pdf.is_file():
            errors.append(f"@key {key}: missing PDF {pdf.relative_to(ROOT)}")
            continue
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if digest != paper["sha256"]:
            errors.append(f"@key {key}: sha256 drift")

    if os.environ.get("RGEN_PUBLIC_RELEASE") == "1":
        import subprocess
        tracked = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "docs/papers/pdf"],
            text=True, capture_output=True).stdout
        for key, paper in papers.items():
            if paper.get("license", {}).get("redistributable") is False:
                if Path(paper["pdf"]).name in tracked:
                    errors.append(
                        f"@key {key}: non-redistributable PDF tracked in a public release")

    if errors:
        for error in errors:
            print(f"check-citations: {error}", file=sys.stderr)
        return 1
    print(f"check-citations: {len(cited)} key(s) cited, manifest and extracts agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
