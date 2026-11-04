# Race-freedom proof

The core claim is a Lean model theorem, not a behavioural test. This page states the
theorem, the model, and the boundary.

## Headline theorem

`RGen.core_races_not_representable` (`spec/lean/RGen/RaceFreedom.lean`):

> For every `Run` over a versioned cell world, and every cell `c`,
> `NoTwoSameExpected c es`: no two events on `c` in the run share an expected generation.

`Run` is the inductive execution semantics in `spec/lean/RGen/Linear/Exec.lean`.
`NoTwoSameExpected` is occurrence-level: for every pair of same-cell events in the run,
their expected generations differ. Accepted commits are a subset of events, so no two
accepted commits share a generation. The quantified statement ranges over all runs, not a
chosen schedule.

The proof is `runExec_no_same_expected`, via per-cell projection (`runCell`) and the
`AppliedExpecteds` invariant: a successful run can only apply a same-cell event when its
expected generation equals the cell's current generation, then advances the generation.
The executable fold and the proof semantics are tied by `runExec_sound` and
`runExec_complete`.

## Consume/post is atomic commit

`RGen.VWorld.take_take_blocks`: after a take, a second take on the same cell fails without
a post. `RGen.VWorld.take_post_commit_equiv`: the deployed
`for (@s <- cell) { ...; cell!(s') }` pattern equals the atomic `VWorld.commit` step.
`RGen.VWorld.commit` and `RGen.Event.apply` advance the generation on both acceptance and
refusal, matching a consume/re-post on every path.

## Decision authority

`RGen.Arm.decision_factors` and `RGen.core_arm_authority`: every arm built with `Arm`
reaches its decision through its consumed cell and nothing else. `Arm.decision` reads only
`w.cell a.cell`. This is functional dependence, not permission: the theorem does not say
who may invoke the arm. `Arm.proofCells` is metadata and is not read by the decision; the
one-shot proof cell is proved separately. The [proof audit](proof-audit.md) records both
gaps (RGA-002, RGA-012).

`RGen.cross_cell_read_not_authority`: if a decision varies with a cell `d` while every
other cell is held equal, it does not factor through the consumed cell `c`, and every
authority set for it must contain `d`. This is the formal "a peek is not a linearization
point" rule. A peek of `d` can be a linearization point *at `d`*; then `d` must be
consumed/authority, not an ambient read. `RGen.peek_not_authority` is the two-cell form.

`RGen.proof_take_once_versioned` / `RGen.core_proof_payloads_consumed`: after an accepted
proof take, the next take rejects; the payload is a snapshot and is not reachable twice.

## Pair matrix

`spec/flows/races.yaml` records every proved arm pair, its class, and the Lean theorem.
`tools/check_race_matrix.py` verifies the class vocabulary, uniqueness, and theorem
existence. There are 32 pairs: 19 `exclusive`, 11 `ordered`, and 2 `independent`.

- `exclusive`: whichever arm runs first, the second arm's guard refuses on the post-state.
- `ordered`: one direction is refused; the other is the serialized/non-retroactive order
  (for example `prove` then `revoke` is admitted and the proof remains a snapshot, while
  `revoke` then `prove` refuses).

Representative theorems:

| Pair | Class | Theorem |
|---|---|---|
| credential prove / revoke | ordered | `credential_prove_revoke_never_after` |
| VP validate / withdraw | exclusive | `vp_validate_withdraw_two_way` |
| VP proveValidated / dispute | ordered | `vp_proveValidated_openDispute_ordered` |
| claim validate / expire | exclusive | `claim_validate_expire_two_way` |
| claim validate / comment | ordered | `claim_validate_blocks_comment` |
| K-Asset approve / reject | exclusive | `kasset_approve_reject_two_way` |
| K-Asset openDispute / proveApproved | ordered | `kasset_openDispute_proveApproved_never_after` |
| K-Asset nest / same child | exclusive | `kasset_nest_same_never_after_arm` |
| oracle decide / expire | exclusive | `oracle_decide_expire_two_way` |
| oracle execute / execute | exclusive | `oracle_execute_execute_never_after` |
| provenance anchor / same hash | exclusive | `provenance_anchor_anchor_same_never_after` |

## Guard reconciliation

The model was partially reconciled with the deployed arms before these proofs: VP withdraw
is proposed-only; VP openDispute accepts proposed/validated with no prior dispute; K-Asset
approve rejects the validator; K-Asset openDispute parties are claimant/validator; nest
checks existing children, scope, and `child.approvedAt < parent.approvedAt`; claim
validation expires late; claim comment has its window; credential renew is issuer-only and
active-only; provenance has a writer list; oracle execute has a rollback/retry path.

The audit found residual divergences that this list does not close: credential revoke
idempotence, expiry boundaries, the missing approver-qualification requirement, nest status
admission and tie handling, caller-chosen claim K-Asset ids, oracle evidence gating, and the
`Identity.update` mapping. The direction of each is in the [proof audit](proof-audit.md)
and `spec/proofs/rigor.yaml`.

`tools/check_arm_guards.py` ties each mutating `.rho` arm to its manifest `cell` and checks
that any declared `transition`/`authority`/`guard_eq` names exist. This is a coarse
hand-encoding check, not a refinement.

## What is not claimed

- No mechanized Rholang semantics and no refinement theorem. The arm-to-model map is
  hand-transcribed; `proved-conformance` remains reserved and unclaimed.
- The model cites the node's single-use COMM / one-message cell / unforgeable names; it
  does not prove them.
- `Run` is a trace semantics over all runs, not an interleaving enumerator.
- The lock-order deadlock theorem remains a lock-order theorem, not scheduler liveness.
- The Python race suite is behavioural regression evidence only. It is not the proof and
  must not be cited as non-representability.

## Reproduce

```sh
cd spec/lean && lake build
cd ../.. && .venv/bin/python tools/check_lean.py --audit
.venv/bin/python tools/check_race_matrix.py
.venv/bin/python tools/check_arm_guards.py
.venv/bin/python tools/check_flows.py
```
