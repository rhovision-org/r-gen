#!/usr/bin/env python3
"""Registry trust gate.

Two rules:
1. Every factory `verify` arm compares the stored record's URI with the requested URI.
2. A source file that resolves one of the verifying factories must call `verify` or be
   allowlisted because it delegates the check to `proveAndCheck` (the proof helper).

This is a source-level gate, not a replacement for the capability register.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "contracts" / "src"
FACTORIES = ("ClaimFactory", "CredentialFactory", "ValuePropositionFactory")
# These files define the factory or pass it to proveAndCheck, which calls verify.
DELEGATED = {"11_credentials.rho", "20_claim.rho", "22_value.rho", "30_oracle.rho"}


def main() -> int:
    errors: list[str] = []
    for path in sorted(SRC.rglob("*.rho")):
        text = path.read_text()
        name = path.name
        for factory in FACTORIES:
            arm = f'contract {factory}(@"verify"'
            if arm in text:
                start = text.index(arm)
                end = text.find("\n      } |", start)
                block = text[start:end if end != -1 else len(text)]
                if 'rec.get("uri").toString() != uri.toString()' not in block:
                    errors.append(f"{path.relative_to(ROOT)}: {factory} verify does not compare the record URI")
        if any(factory in text for factory in FACTORIES):
            if not any(f'{factory}!("verify"' in text for factory in FACTORIES):
                if name not in DELEGATED:
                    errors.append(f"{path.relative_to(ROOT)}: resolves a verifying factory without a verify call "
                                  "and is not in the delegated allowlist")
    for error in errors:
        print(f"check_registry_trust: {error}")
    if errors:
        print(f"check_registry_trust: {len(errors)} error(s)")
        return 1
    print(f"check_registry_trust: {len(FACTORIES)} factory verifies and the delegated allowlist agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
