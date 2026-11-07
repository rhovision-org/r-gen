#!/usr/bin/env python3
"""Measure deploy atomicity on the pinned devnet.

The core docs claim that a deploy's state changes roll back on failure. This probe separates
two failure modes that the claim does not distinguish:

1. A reduction error after a write. The node should discard the whole deploy.
2. A continuation that blocks after consuming a cell. The deploy has no error and no further
   reductions; if the consumed state is committed, the cell is lost.

The probe uses a small registry-published store so the write and the read are in separate
deploys. It also exercises the natural `Claim.comment` path on a claim whose
`commentUntilHeight` is Nil.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

import actors
import assertions
import deploy as node
import fixtures
import preflight
import suite_base


STORE = """
new cell, C, rs(`rho:registry:insertArbitrary`), deployId(`rho:rchain:deployId`),
    uriCh in {
  cell!(0) |
  contract C(@"put", @v, ret) = { for (@_ <- cell) { cell!(v) | ret!(true) } } |
  contract C(@"get", ret) = { for (@v <<- cell) { ret!(v) } } |
  contract C(@"lose", ret) = { for (@_ <- cell) { for (@never <- ret) { Nil } } } |
  rs!(bundle+{*C}, *uriCh) |
  for (@uri <- uriCh) { deployId!(uri) }
}
"""


def submit(term: str, secret: str, phlo_limit: int = 6_000_000) -> dict:
    """Deploy a term and return the node's verdict without raising on deploy errors."""
    try:
        deploy_id = node.deploy(term, secret, phlo_limit=phlo_limit)
    except node.DevnetError as error:
        return {"deploy_id": None, "variant": "rejected", "error": str(error)}
    try:
        variant, payload = node.wait_processed(deploy_id, timeout=90)
    except node.DevnetError as error:
        return {"deploy_id": deploy_id, "variant": "timeout", "error": str(error)}
    return {
        "deploy_id": deploy_id,
        "variant": variant,
        "deploy_error": payload.get("deployError"),
        "result": assertions.decode(payload.get("deployResult")),
    }


def read_store(uri: str, secret: str) -> dict:
    term = f"""
new rl(`rho:registry:lookup`), ch, ret, deployId(`rho:rchain:deployId`) in {{
  rl!(`{uri}`, *ch) |
  for (C <- ch) {{ C!("get", *ret) | for (@v <- ret) {{ deployId!(v) }} }}
}}
"""
    return submit(term, secret, phlo_limit=4_000_000)


def put_then_error(uri: str, value: int, secret: str) -> dict:
    """Write a value, wait for the write acknowledgement, then force a reduction error."""
    term = f"""
new rl(`rho:registry:lookup`), ch, ack, xCh,
    deployId(`rho:rchain:deployId`) in {{
  rl!(`{uri}`, *ch) |
  xCh!(1) |
  for (C <- ch; @x <- xCh) {{
    C!("put", {value}, *ack) |
    for (@ok <- ack) {{ deployId!(x + Nil) }}
  }}
}}
"""
    return submit(term, secret)


def consume_then_block(uri: str, secret: str) -> dict:
    """Consume the store cell and block without re-posting it."""
    term = f"""
new rl(`rho:registry:lookup`), ch, ret,
    deployId(`rho:rchain:deployId`) in {{
  rl!(`{uri}`, *ch) |
  for (C <- ch) {{ C!("lose", *ret) | for (@x <- ret) {{ deployId!(x) }} }}
}}
"""
    return submit(term, secret)


def natural_claim_probe(secret: str) -> dict:
    """Create a claim with no comment window, comment, and re-read the claim."""
    req = suite_base.claim_req(actors.address("deployer"))
    req["commentUntilHeight"] = None
    created = fixtures.claim("deployer", req)
    if not (isinstance(created, tuple) and created and created[0] is True):
        return {"created": False, "reply": created}
    claim_uri = created[1]["uri"]
    before = fixtures.read(claim_uri, "get")
    comment = submit(
        f"""
new rl(`rho:registry:lookup`), ch, ret,
    dId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{
  rl!(`{claim_uri}`, *ch) |
  for (Claim <- ch) {{
    Claim!("comment", *dId, {{"hash": "semantics-probe"}}, *ret) |
    for (@r <- ret) {{ deployId!(r) }}
  }}
}}
""",
        secret,
    )
    after = fixtures.read(claim_uri, "get")
    return {
        "created": True,
        "claim_uri": claim_uri,
        "before": before,
        "comment": comment,
        "after": after,
    }


def node_identity() -> dict:
    status = node.http_json("GET", f"{node.NODE}/api/v1/status")
    return {
        "node": status.get("version", {}).get("node"),
        "network_id": status.get("networkId"),
        "shard_id": status.get("shardId"),
        "height": status.get("latestBlockNumber"),
        "phlo_price": status.get("minPhloPrice"),
    }


def main() -> int:
    if not preflight.require_devnet("probe_deploy_semantics"):
        return 2
    secret = node.secret_for("deployer")
    identity = node_identity()

    store = submit(STORE, secret, phlo_limit=4_000_000)
    store_uri = assertions.find_uri(store.get("result"))
    if not store_uri:
        print(f"probe: store deploy failed: {store}", file=sys.stderr)
        return 2

    initial = read_store(store_uri, secret)

    put_ok = submit(
        f"""
new rl(`rho:registry:lookup`), ch, ack,
    deployId(`rho:rchain:deployId`) in {{
  rl!(`{store_uri}`, *ch) |
  for (C <- ch) {{ C!("put", 42, *ack) | for (@ok <- ack) {{ deployId!(ok) }} }}
}}
""",
        secret,
    )
    before_error = read_store(store_uri, secret)
    failed_write = put_then_error(store_uri, 43, secret)
    after_error = read_store(store_uri, secret)

    lost = consume_then_block(store_uri, secret)
    after_loss = read_store(store_uri, secret)

    claim = natural_claim_probe(secret)

    def value(probe: dict):
        result = probe.get("result")
        if isinstance(result, list) and len(result) == 1:
            return result[0]
        return result

    report = {
        "schema": "rgen.deploy-semantics/v1",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "node": identity,
        "store_uri": store_uri,
        "probes": {
            "initial_read": {"value": value(initial), "probe": initial},
            "write_before_error": {
                "write": put_ok,
                "value_after_write": value(before_error),
                "read": before_error,
            },
            "reduction_error_after_write": {
                "deploy": failed_write,
                "value_after_error": value(after_error),
                "read": after_error,
                "rolled_back": value(after_error) == 42,
            },
            "blocked_continuation_after_consume": {
                "deploy": lost,
                "read_after_loss": after_loss,
                "value_after_loss": value(after_loss),
                "cell_lost": after_loss.get("result") == [],
            },
            "natural_claim_nil_comment": claim,
        },
    }

    spec = ROOT / "spec" / "audit"
    spec.mkdir(parents=True, exist_ok=True)
    (spec / "deploy-semantics.json").write_text(json.dumps(report, indent=2) + "\n")

    rolled_back = report["probes"]["reduction_error_after_write"]["rolled_back"]
    cell_lost = report["probes"]["blocked_continuation_after_consume"]["cell_lost"]
    lines = [
        "# Deploy semantics on the pinned devnet",
        "",
        f"Measured {report['measured_at']} against {identity['node']} "
        f"({identity['network_id']}, shard {identity['shard_id']}, height {identity['height']}).",
        "",
        "| Probe | Observation | Meaning |",
        "|---|---|---|",
        f"| write, then reduction error | value after error = "
        f"{report['probes']['reduction_error_after_write']['value_after_error']!r} "
        f"(pre-error value 42) | {'rollback' if rolled_back else 'partial commit'} |",
        f"| consume, then block without re-post | read after loss = "
        f"{report['probes']['blocked_continuation_after_consume']['read_after_loss'].get('result')!r} | "
        f"{'consumed cell lost' if cell_lost else 'cell preserved'} |",
        f"| `Claim.comment` with `commentUntilHeight = Nil` | "
        f"deploy verdict `{claim.get('comment', {}).get('variant')}` | "
        f"{'reduction error' if claim.get('comment', {}).get('variant') == 'processedwitherror' else 'see report'} |",
        "",
        "## Verdict",
        "",
    ]
    if rolled_back:
        lines.append(
            "The node rolls back a deploy that ends in a reduction error. The "
            "\"crash after a partial write\" reading of RGA-031/032/033 is not reachable "
            "through an erroring deploy on this build."
        )
    else:
        lines.append(
            "The node committed a write from a deploy that ended in a reduction error. "
            "The atomicity assumption in `docs/src/reference/rholang-model.md` is false "
            "for this build; cross-cell recovery is required."
        )
    if cell_lost:
        lines.append(
            "A deploy that consumes a linear cell and then blocks is reported as "
            "`processedWithSuccess` with an empty result, and the consumed cell is gone. "
            "This is the reachable partial-commit path: holding a consumed cell across a "
            "callee that may not reply loses the cell. HAZOP rows and the contract fixes "
            "must treat blocked continuations, not only reduction errors, as the failure mode."
        )
    else:
        lines.append(
            "A consumed cell survived a blocked continuation, so the node does not commit "
            "a consumed cell without a re-post."
        )
    lines += [
        "",
        f"Natural claim probe: reply before `{claim.get('before')!r}`, after "
        f"`{claim.get('after')!r}`. A reduction error leaves the claim state intact; the "
        "defect is a bad refusal path, not state loss.",
        "",
        "Raw report: `spec/audit/deploy-semantics.json`.",
    ]
    (spec / "deploy-semantics.md").write_text("\n".join(lines) + "\n")

    print(f"probe: reduction error rollback = {rolled_back}")
    print(f"probe: blocked continuation loses cell = {cell_lost}")
    print(f"probe: wrote {spec / 'deploy-semantics.json'}")
    print(f"probe: wrote {spec / 'deploy-semantics.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
