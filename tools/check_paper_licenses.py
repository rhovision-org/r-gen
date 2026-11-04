#!/usr/bin/env python3
"""Report paper redistribution status; fail a public-release build if needed."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "papers" / "manifest.json"


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    public = os.environ.get("RGEN_PUBLIC_RELEASE") == "1"
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "docs/papers/pdf"],
        text=True, capture_output=True).stdout

    bad = []
    for paper in manifest["papers"]:
        status = paper.get("license", {})
        redistributable = status.get("redistributable", False)
        name = Path(paper["pdf"]).name
        print(f"{paper['key']:24} {status.get('status', 'unknown'):36} "
              f"redistributable={redistributable} tracked={name in tracked}")
        if public and not redistributable and name in tracked:
            bad.append(paper["key"])

    if bad:
        print(f"check-paper-licenses: non-redistributable tracked in public release: {bad}",
              file=sys.stderr)
        return 1
    print("check-paper-licenses: status recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
