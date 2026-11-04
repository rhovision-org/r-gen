"""Resolve the r-cash checkout and its devnet files.

The default is a sibling checkout named ``Rholphin``. ``RCASH_DIR`` overrides it, which is
how CI points at its ``rholo`` checkout. Config files keep the sibling path as the local
fallback; every reader should go through this module so a fork or CI checkout needs no
symlink.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RCASH = ROOT.parent / "Rholphin"


def rcash_dir() -> Path:
    value = os.environ.get("RCASH_DIR")
    return Path(value).expanduser().resolve() if value else DEFAULT_RCASH.resolve()


def keys_path() -> Path:
    return rcash_dir() / ".devnet" / "keys.json"


def state_path() -> Path:
    return rcash_dir() / ".devnet" / "v3-install.json"


def manifest_path() -> Path:
    return rcash_dir() / "deployments" / "devnet-v4.json"


def _configured(value: str | None, default: Path) -> Path:
    if os.environ.get("RCASH_DIR") or not value:
        return default
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def configured_manifest(value: str | None = None) -> Path:
    return _configured(value, manifest_path())


def configured_state(value: str | None = None) -> Path:
    return _configured(value, state_path())
