"""Rholang term construction helpers for the behavioural suites."""

from __future__ import annotations

import json


class Raw(str):
    """A fragment emitted verbatim (for `*dId` and similar)."""


def q(value: str) -> str:
    return json.dumps(value)


def enc(value) -> str:
    if isinstance(value, Raw):
        return str(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return q(value)
    if value is None:
        return "Nil"
    if isinstance(value, list):
        return "[" + ", ".join(enc(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{q(key)}: {enc(item)}" for key, item in value.items()) + "}"
    raise TypeError(f"cannot encode {type(value)!r}")


def call_term(uri: str, arm: str, args=()) -> str:
    sent = [q(arm), *(enc(arg) for arg in args), "*ret"]
    return (
        "new rl(`rho:registry:lookup`), ch, ret, dId(`rho:rchain:deployerId`), "
        "deployId(`rho:rchain:deployId`) in {\n"
        f"  rl!(`{uri}`, *ch) |\n"
        "  for (C <- ch) {\n"
        f"    C!({', '.join(sent)}) |\n"
        "    for (@r <- ret) { deployId!(r) }\n"
        "  }\n"
        "}\n"
    )


def call_no_deployer(uri: str, arm: str, args=()) -> str:
    sent = [q(arm), *(enc(arg) for arg in args), "*ret"]
    return (
        "new rl(`rho:registry:lookup`), ch, ret, deployId(`rho:rchain:deployId`) in {\n"
        f"  rl!(`{uri}`, *ch) |\n"
        "  for (C <- ch) {\n"
        f"    C!({', '.join(sent)}) |\n"
        "    for (@r <- ret) { deployId!(r) }\n"
        "  }\n"
        "}\n"
    )
