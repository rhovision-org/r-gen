#!/usr/bin/env python3
"""Copy the page-cited extracts into mdBook's source tree.

The full PDF archive stays under docs/papers/ and is not copied into the mdBook source; it
is third-party material and may not be redistributable.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "papers" / "extract"
DST = ROOT / "docs" / "src" / "papers" / "extracts"


def main() -> int:
    DST.mkdir(parents=True, exist_ok=True)
    for path in DST.glob("*.md"):
        path.unlink()
    for path in sorted(SRC.glob("*.md")):
        shutil.copyfile(path, DST / path.name)
    print(f"sync-papers: copied {len(list(DST.glob('*.md')))} extract(s) to "
          f"{DST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
