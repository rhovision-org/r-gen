# Deploy semantics on the pinned devnet

> **Measured:** 2026-11-07 against RChain Node 0.1.0
> (`e2d073dcd02f1e560ccb84749937138a1e184b0b`), devnet shard `/root`
> **Probe:** `harness/probe_deploy_semantics.py`
> **Raw record:** `spec/audit/deploy-semantics.json`

The core docs claim that a deploy's state changes roll back on failure. The probe separates two
failure modes that the claim does not distinguish.

| Probe | Observation | Meaning |
|---|---|---|
| write a value, then force a reduction error | the value after the error is the pre-error value | the erroring deploy was rolled back |
| consume a linear cell, then block without re-posting | the follow-up read succeeds with an empty result; the cell is gone | a blocked continuation commits the consumed state |
| `Claim.comment` on a claim with `commentUntilHeight = Nil` | deploy verdict `processedwitherror`; the claim re-reads unchanged | a reduction error is not state loss |

## Verdict

- **Reduction errors roll back.** A deploy that ends in an error does not commit a write that
  preceded the error.
- **Blocked continuations commit.** A deploy with no error and no remaining reductions can leave a
  consumed cell empty. This is the reachable partial-commit path on this build.

The second point is the important one. The old RGA-031/032/033 windows were not reachable through
an erroring deploy, but they were reachable through a callee that never replies. Holding a
consumed `directoryState`, `claimState`, or `kState` across a cross-contract call is therefore a
defect even under rollback.

## What changed

- Identity create writes a reservation and releases `directoryState` before minting; the mint and
  finalize steps re-consume the directory. A blocked mint leaves a reservation, not a lost cell.
- Claim validate writes a `validating` receipt and releases the claim cell before `makeKAsset`;
  `resume` re-drives the commit.
- Proof issuance sends `bundle+{*Proof}` on a caller channel and no longer inserts it into the
  registry, so `proof` and `proveApproved` do not hold their credential/K-Asset cell across a
  registry insert.
- Oracle execute writes `executing`, releases the case cell, and can re-drive an `executing` case.

## Reproduce

```bash
make probe-deploy-semantics
```

The probe leaves three claims and a small registry-published store on the devnet. It is safe to
run on the disposable local devnet; it does not touch testnet or value.

## Limits

- The measurement is specific to the pinned node build. A node upgrade invalidates it.
- The blocked-continuation probe uses a deliberately non-replying contract. It demonstrates the
  runtime behavior; it does not enumerate every callee that could block.
