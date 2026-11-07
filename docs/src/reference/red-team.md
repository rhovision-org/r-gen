# Red team: current-core exploits

> **Run:** 2026-11-07
> **Node:** RChain Node 0.1.0 (`e2d073dcd02f1e560ccb84749937138a1e184b0b`)
> **Network:** local devnet, shard `/root`, no value
> **Machine-readable record:** `spec/audit/redteam.yaml`

The red team is a set of executable deploys against the installed contracts. It is regression
evidence, not a proof. Every probe records what it observed; `RGEN_EXPECT=fixed` turns a
post-fix mismatch into a failure.

## Deploy semantics first

`harness/probe_deploy_semantics.py` measures two failure modes:

| Probe | Observation | Meaning |
|---|---|---|
| write, then reduction error | the write is discarded | the node rolls back an erroring deploy |
| consume, then block without re-post | the consumed cell is gone; the follow-up read succeeds with an empty result | a blocked continuation commits the consumed state |

The second row is the reachable partial-commit path. It is why holding a consumed cell across a
callee that may not reply is a defect even though erroring deploys roll back. See
[Deploy semantics](deploy-semantics.md).

## Results

| ID | Attack | Observed after repair |
|---|---|---|
| RT-001 | two identity creates for one address | one succeeds, the other refuses `duplicate`; not reproduced as a duplicate in three attempts; the reservation protocol removes the window |
| RT-002 | two claim validations in one deploy | exactly one succeeds |
| RT-003 | nest with a failing final parent check | proof is private and re-mintable; the parent is unchanged |
| RT-004 | third party takes a proof URI | **fixed**: `prove` returns no URI; the capability goes only to the caller's private channel |
| RT-005 | non-party `Claim.resume` | refused `not party`; `validating` is unreachable without a blocked mint |
| RT-006 | comment on a claim with `commentUntilHeight = Nil` | **fixed**: deterministic refusal; the claim survives |
| RT-007 | claim with a free-string `subjectRef` | **fixed**: refused `fields` |
| RT-008 | credential issued without `level` | **fixed**: refused `fields`; `scopeMatches` is total |
| RT-009 | oracle open with a past deadline | **fixed**: refused `case fields` |
| RT-010 | oracle open with caller-chosen parties | refused; a dummy `Apply` cannot touch a real subject |
| RT-011 | provenance record for a victim `assetRef` | **accepted**: provenance is advisory and no core arm uses it as authority |
| RT-012 | permissionless execute crank | **accepted**: applies the stored decision, cannot choose the outcome |
| RT-013 | permissionless `proveApproved` | **accepted**: private capability, caller-paid, no registry entry |
| RT-014 | nest above the 32-child cap | refused before any proof action |
| RT-020 | VP validator opens a dispute | **fixed**: the caller is authenticated as itself |
| RT-021 | VP validation after the deadline | **fixed**: refused `deadline` |
| RT-022 | oracle decide after the case deadline | **fixed**: refused `expired` |
| RT-023 | claim records the proved credential | **fixed**: the receipt and K-Asset record the proved URI |

## Contract changes exercised

- Identity create is a reservation, mint, and two-step finalize; `resume` is subject-only.
- Claim validation writes a `validating` receipt, releases the claim cell, mints, then commits;
  `resume` re-drives the commit and never mints.
- Proofs are private capabilities sent on a caller channel; `proofCh!(bundle+{*Proof})` replaces
  the registry insert.
- Claim comment normalizes a Nil window; claim create validates `subjectRef`; credential issue
  validates its fields; VP and oracle validation/decision check the deadline; provenance prepends
  the creator to the writer list; identity update preserves omitted fields.

## Remaining accepted items

- **RT-011 provenance spoofing.** Any authenticated deployer can create a provenance record for
  an arbitrary `assetRef`. It is advisory: claims, validations, approvals and decisions do not
  read it. Binding it needs an asset registry or a subject-info capability.
- **RT-013 proof minting.** `proveApproved` is permissionless and mints a fresh proof on every
  call. The proof is private to the caller, there is no registry entry, and the caller pays phlo.
- **RT-012 execute crank.** `execute` is permissionless by design; it applies the stored decision
  and `Apply.applyDecision` is idempotent.
- **Deadline and retry edges.** The execute receipt records `attempts: 1`; a decided case with a
  permanently failing apply has no terminal close path. Both are accepted in the workflow HAZOP.

## Reproduce

```bash
make probe-deploy-semantics   # writes spec/audit/deploy-semantics.{json,md}
make redteam                  # writes spec/audit/redteam.yaml and deployments/redteam-results.json
RGEN_EXPECT=fixed make redteam
```

`make redteam` exits 2 if the devnet is not healthy. It never treats a missing node as a pass.
