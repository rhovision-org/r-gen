# Concurrency and proofs

This page states the model's concurrency argument and the rholo principles it mirrors.

## Linear cells

Every entity is a cell with one message. The trace model (`RGen.Linear.Cell`) enforces:

- **D1** — a peek followed by a put is not a committed update; a put with no take is
  refused.
- **D2** — a take with no put is not well formed (it leaves the cell held).
- **D3** — a nested call on a held cell is blocked.

`peek_then_put_rejected`, `put_without_take_rejected`, `take_without_put_not_wf`, and
`nested_call_rejected` are the model's names; `D1`–`D3` are the stable aliases.

## Framing and independence

`run_frame` says a successful trace leaves every cell outside its footprint unchanged,
both its value and its occurrence count in the held list. `run_agree` says two runs whose
states agree on the footprint and on a protected set produce results that agree on the
same set; it is the induction used to compose traces.

`disjoint_cells_commute` states that traces with disjoint footprints commute on the
store. The held list is deliberately byte-level (a `take` conses without deduplicating),
so two disjoint traces can produce the same store with the held cells in a different
order. `disjoint_cells_commute_wf` therefore states the exact result equality for two
well-formed traces started from an empty held set: both end with the empty held set, and
the stores agree everywhere.

`disjoint_cells_commute_wf` does not depend on the scheduler picking a winner. It is a
property of the trace semantics: independent entities do not interact, and shared cells
serialize.

## Commits

The application model uses `World`/`commit`:

- `commit_commute` — commits on different cells commute.
- `commit_same_cell` — a second commit on the same cell composes with the first; the
  second sees the first's post-state, so two operations cannot both decide from the same
  pre-state.
- `commit_preserves_other` — a commit on one cell leaves every other cell alone.

`independent_commute` and `shared_serializes` are the stable `L1`/`L2` names.

## Acquisition order

`RGen.Concurrency` assigns ranks:

| Holder | May acquire | Rank |
|---|---|---|
| any non-proof | `Proof.take` | n → 0 |
| `Claim` | credential proof | 3 → 1 |
| `ValueProposition` | credential proof | 2 → 1 |
| `OracleCase` | credential proof | 3 → 1 |
| `K-Asset` | credential proof | 4 → 1 |
| `K-Asset` | value-proposition proof | 4 → 2 |
| `K-Asset` | child K-Asset | **no edge** (two-phase) |

`MayAcquire` has no `KAsset → KAsset` edge. Nesting takes child proofs in a phase that
holds no business cell, so the model does not claim a recursive lock. `mayAcquire_rank_strict`
shows every edge strictly decreases rank, `mayAcquire_acyclic` shows the acquisition
relation has no cycle, and `deadlock_free_of_rank` is the general rank argument.

This is a lock-order theorem under the finite-cell/no-dynamic-locks hypothesis, not
global scheduler liveness. Rholo's Law 20 global deadlock-freedom was deleted as
unprovable without a finiteness hypothesis; the same caution applies.

## Non-representability theorem

`RGen.core_races_not_representable` (`spec/lean/RGen/RaceFreedom.lean`) quantifies over
**all** `Run`s of the versioned-cell semantics: for every cell `c`, no two events on `c`
share an expected generation. Accepted commits are a subset of events. The proof is
`runExec_no_same_expected`, via per-cell projection and the `AppliedExpecteds` invariant.

`RGen.core_arm_authority` says every `Arm` decision factors through its consumed cell;
proof payloads are consumed one-shot values, not ambient reads.
`RGen.cross_cell_read_not_authority` is the formal rule that a decision varying with a
non-consumed cell does not factor through the consumed cell; any authority set must
contain the other cell. A peek can be a linearization point at that other cell, but then
it must be authority, not a peek.

The pair matrix `spec/flows/races.yaml` records 32 proved pairs (19 exclusive, 12 ordered, 1 independent)
and is checked by `tools/check_race_matrix.py`. The model's arm encoding is hand-written;
`tools/check_arm_guards.py` ties each mutating `.rho` arm to its consumed cell. There is no
mechanized Rholang refinement.

## Linearization points

Proof issuance is the linearization point for every credential-gated arm:

- `Credential.prove` requires an active credential at the stated height and returns a
  one-shot proof; it does not change the credential.
- A revoke or dispute consumes the same cell, so a second operation cannot both read the
  pre-state and commit against it. `prove_after_revoke` and `prove_after_dispute` show
  the refusal from the post-state.
- The proof is a snapshot; a later revoke or dispute is non-retroactive. This is by
  design, not a gap.

Registries (`factoryState`, `claimRegistryState`, `vpRegistryState`, `directoryState`)
serialize creation only. Validation, approval, decision, nesting, and provenance remain
per-entity.

## rholo principles mirrored

The model cites the node's formal layer rather than re-proving it: single-use COMM
(`Reduce.comm`), unforgeable names (`reduce_freeVars_subset`), matcher linearity,
append-only registry reasoning, and closure-disjointness commutation
(`effect_commute_of_disjoint_closure`). The application invariants are stated here; the
node supplies the ingredients.

## What is not claimed

- No mechanized Rholang semantics and no refinement theorem. The arm-to-model map is
  hand-transcribed; `proved-conformance` is reserved and unclaimed.
- The theorem is over the model's `Run` semantics, not an enumeration of the deployed
  scheduler's interleavings. The behavioural race suite is regression evidence only.
- No claim that the deployed `nest` pre-pass is authoritative: the child proof is.
- No global fairness or starvation-freedom claim.
