#!/usr/bin/env python3
"""Actors, funding and component resolution for the behavioural suites."""

from __future__ import annotations

import json
import time
from pathlib import Path

from assertions import one, root_uri, manifest

import deploy as node

PING = 'new deployId(`rho:rchain:deployId`) in { deployId!(1) }'


def keys() -> dict:
    return node.load_keys()


def public(name: str = "deployer") -> str:
    return keys()[name]["public"]


def address(name: str = "deployer") -> str:
    return keys()[name]["address"]


def invoke(uri: str, arm: str, args=None, key: str = "deployer",
           phlo_limit: int = 8_000_000):
    from terms import call_term
    return one(call_term(uri, arm, args or ()), key=key, phlo_limit=phlo_limit)


def resolve(component: str, key: str = "deployer"):
    root_key = component if component.startswith("component:") else f"component:{component}"
    reply = invoke(root_uri(), "resolve", [root_key], key=key)
    if not (isinstance(reply, tuple) and reply[0] is True):
        raise AssertionError(f"resolve {component}: {reply!r}")
    return reply[1]


def ensure_vault(name: str, min_phlo: int = 8_000_000) -> None:
    if name == "deployer":
        return
    try:
        one(PING, key=name, phlo_limit=min_phlo)
        return
    except node.DevnetError as error:
        if "insufficient funds" not in str(error):
            raise

    # The local devnet deployer is genesis-funded. The faucet allows one drip per
    # address, so a long suite run cannot top up through it; a native REV transfer can.
    if not node.REMOTE:
        try:
            node.transfer_rev("deployer", public(name))
            one(PING, key=name, phlo_limit=min_phlo)
            print(f"  top-up {name}")
            return
        except node.DevnetError:
            pass

    last: Exception | None = None
    for _ in range(8):
        try:
            node.faucet(address(name))
        except Exception as error:
            last = error
        time.sleep(2)
        try:
            one(PING, key=name, phlo_limit=min_phlo)
            return
        except node.DevnetError as error:
            if "insufficient funds" not in str(error):
                raise
            last = error
    raise AssertionError(f"actor {name} has no phlo: {last}")


def block_height() -> int:
    term = """
new bd(`rho:block:data`), ch, deployId(`rho:rchain:deployId`) in {
  bd!(*ch) |
  for (@n, @sender, @timestamp <- ch) { deployId!(n) }
}
"""
    height = one(term)
    if not isinstance(height, int):
        raise AssertionError(f"block height: {height!r}")
    return height


def rcash_root_uri() -> str:
    cfg = json.loads((Path(__file__).resolve().parent.parent
                      / "configs" / "devnet.json").read_text())
    from rcash_paths import configured_manifest
    path = configured_manifest(cfg["rcash_manifest"])
    return json.loads(path.read_text())["root_uri"]


def ensure_account(name: str) -> str:
    term = f"""
new rl(`rho:registry:lookup`), rootCh, afCh, ac, oCh,
    deployId(`rho:rchain:deployId`) in {{
  rl!(`{rcash_root_uri()}`, *rootCh) |
  for (Root <- rootCh) {{
    Root!("resolve", "component:account-factory", 1, *afCh) |
    for (@(true, afUri, _) <- afCh) {{
      rl!(afUri, *ac) |
      for (AccountFactory <- ac) {{
        AccountFactory!("getOrCreate", "{public(name)}".hexToBytes(), *oCh) |
        for (@(true, account, ownerId) <- oCh) {{ deployId!(ownerId) }}
      }}
    }}
  }}
}}
"""
    owner = one(term, key=name, phlo_limit=4_000_000)
    if not isinstance(owner, str):
        raise AssertionError(f"account for {name}: {owner!r}")
    return owner


def fund(name: str, amount: int = 2_000) -> int:
    """Mint REV into an actor's r-cash account and return the new balance."""
    term = f"""
new rl(`rho:registry:lookup`), rootCh, afCh, ac, oCh, fCh, bCh,
    ertpCh, revIssuerCh, purseCh, fundCh, wdCh, depCh,
    deployId(`rho:rchain:deployId`), deployerId(`rho:rchain:deployerId`) in {{
  rl!(`{rcash_root_uri()}`, *rootCh) |
  rl!(`rho:rchain:ertp`, *ertpCh) |
  for (Root <- rootCh; @(_, ERTP) <- ertpCh) {{
    Root!("resolve", "component:account-factory", 1, *afCh) |
    for (@(true, afUri, _) <- afCh) {{
      rl!(afUri, *ac) |
      for (AccountFactory <- ac) {{
        AccountFactory!("getOrCreate", "{public(name)}".hexToBytes(), *oCh) |
        for (@(true, account, ownerId) <- oCh) {{
          @account!("depositFacet", "REV", *fCh) |
          for (@fr <- fCh) {{
            match fr {{
              (true, facet) => {{
                @ERTP!("getRevIssuer", *revIssuerCh) |
                for (@(revBrand, revIssuer) <- revIssuerCh) {{
                  @revIssuer!("makeEmptyPurse", *purseCh) |
                  for (@(true, purse) <- purseCh) {{
                    @purse!("revFund", *deployerId, 100000, *fundCh) |
                    for (@_ <- fundCh) {{
                      @purse!("withdraw", (revBrand, {amount}), *wdCh) |
                      for (@(true, payment) <- wdCh) {{
                        @facet!("deposit", payment, *depCh) |
                        for (@d <- depCh) {{
                          match d {{
                            (true, balance) => {{ deployId!([ownerId, balance]) }}
                            _ => {{ deployId!(d) }}
                          }}
                        }}
                      }}
                    }}
                  }}
                }}
              }}
              _ => {{ deployId!(fr) }}
            }}
          }}
        }}
      }}
    }}
  }}
}}
"""
    reply = one(term, key=name, phlo_limit=4_000_000)
    if not (isinstance(reply, list) and len(reply) == 2 and isinstance(reply[1], int)):
        raise AssertionError(f"fund {name}: {reply!r}")
    return reply[1]


def balance(name: str = "deployer") -> int:
    term = f"""
new rl(`rho:registry:lookup`), rootCh, afCh, ac, oCh, bCh,
    deployId(`rho:rchain:deployId`), deployerId(`rho:rchain:deployerId`) in {{
  rl!(`{rcash_root_uri()}`, *rootCh) |
  for (Root <- rootCh) {{
    Root!("resolve", "component:account-factory", 1, *afCh) |
    for (@(true, afUri, _) <- afCh) {{
      rl!(afUri, *ac) |
      for (AccountFactory <- ac) {{
        AccountFactory!("getOrCreate", "{public(name)}".hexToBytes(), *oCh) |
        for (@(true, account, ownerId) <- oCh) {{
          @account!("balance", *deployerId, "REV", *bCh) |
          for (@b <- bCh) {{ deployId!(b) }}
        }}
      }}
    }}
  }}
}}
"""
    reply = one(term, key=name, phlo_limit=4_000_000)
    if not (isinstance(reply, tuple) and reply[0] is True and isinstance(reply[1], int)):
        raise AssertionError(f"balance {name}: {reply!r}")
    return reply[1]
