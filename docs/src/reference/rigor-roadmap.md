# Proof-rigor roadmap

This page is the plan for making the primitives more rigorously proved, given the audit. It is
deliberately a ladder: each rung is a stronger claim with a different evidence standard. Most of
the current suite is R1. The roadmap targets R2 for the core arms and leaves R3/R4 out of scope.

## The rigor ladder

| Level | Claim | Evidence | Current |
|---|---|---|---|
| R0 | Prose invariant | Review and tests | Supporting material only |
| R1 | Theorem over the hand-transcribed model | Lean, axiom audit | 39 Pareto theorems |
| R2 | Model guard anchored to a decision table and deployed vectors | R1 plus a table generated from the contract and asserted by a suite | Target for the 35 `proved-model` arms |
| R3 | Mechanized extraction or refinement of a Rholang subset | A semantics and a refinement theorem | Not planned |
| R4 | Full Rholang/node refinement | Mechanized Rholang semantics, COMM, names, phlo | Out of scope |

R2 is not refinement. It says the model's accept/refuse decision matches an explicit table for the
tested parameter domains, and that the deployed contract agrees with the same table. It does not
say the table is complete over unbounded inputs. The target set is the 35 `proved-model` arms.

## Work items

| ID | Work | Why it raises the level |
|---|---|---|
| LR-00 | Add `Arm` values for `Identity.update`, `IdentityFactory.create`, `ValueProposition.comment`; move `claimReject`, `oracleFinish`, `oracleRollback` to the model-only ledger | Removes a mapping falsehood and makes every deployed mutating arm point at a real step |
| LR-01 | Add `Arm.guard : σ → π → Bool`, `Arm.apply_iff_guard`, `Arm.step_none_iff_not_guard`; per-arm `*_guard_eq` and `*_reason_cases` over explicit tables | Turns a one-line name check into a guard-level obligation; exposes the divergences |
| LR-02 | Add `VWorld.set_commute`, `VWorld.commit_commute`, `VWorld.commit_preserves_other`, `take_post_commute`; `runExec_append`, `runExec_commute_distinct`, `runExec_frame` | Ties the versioned execution layer to the independence layer |
| LR-03 | Give `proofCells` a consumption relation; prove `Arm.proofCells_consumed_before_commit` and `core_no_proof_reuse_across_arms` | Makes the one-shot proof a property of arm runs, not a standalone cell |
| LR-04 | Add `core_independent_arms_commute`, `core_cross_cell_frame`, `core_shared_cell_serializes`; restate authority as dependence, not permission | States precisely what the concurrency layer proves |
| LR-05 | Close the pair matrix to the 48 distinct pairs over the six modeled cells, or mark unmodeled pairs with a reason | Removes the “32 rows implies complete” overclaim |
| LR-06 | Define `proved-conformance` as theorem + emitted vector + deployed-suite assertion; add `tools/check_conformance.py` | Makes the status mean something and gives first candidates (revoke, validate, approve, execute) |
| LR-07 | Add `check_lean.py --audit-coverage`; require every public theorem in `Audit.lean` | Stops new theorems from escaping the axiom audit |
| LR-08 | Resolve every divergence in DIV-001…016: align the model or record an abstraction with a soundness argument | Removes model-stricter and effect-omitting gaps |

### Phase 2 progress

| Item | Status | What changed |
|---|---|---|
| LR-00 | done | `ProfileState.updateProfile` and `IdentityPatch`; Arm values for identity update, identity create, and VP comment; model-only arms listed in `spec/proofs/rigor.yaml` |
| LR-01 | done | `*_guard_eq` theorems for all 32 mutating proved-model arms and a manifest `guard_eq` field; the three read-only arms have no guard obligation |
| LR-02 | partial | `VWorld.set_commute`, `VWorld.commit_commute`, `Event.apply_commute_distinct`, `core_independent_arms_commute`, and `runExec_append`; a full `runExec` commute theorem remains |
| LR-03 | partial | proof-cell membership theorems for seven arms; the trace-consumption relation is pending |
| LR-04 | done | Independent arm events commute to the same final world; `core_independent_cells_commute` remains as a compatibility alias |
| LR-05 | partial | The model-only finish/execute row is removed; the matrix is 32 rows against 48 distinct modeled pairs |
| LR-06 | partial | `check_conformance.py` enforces theorem + vector + suite; 0 arms are promoted because no deployed suite assertion is recorded |
| LR-07 | done | `check_lean.py --audit-coverage` requires every Pareto `#check` in `Audit.lean`; 83 Pareto checks and 192 axiom checks pass |
| LR-08 | partial | Identity update is now modeled; the other divergences remain in the ledger |

The guard count is 32 of 35 proved-model arms; the remaining three are read-only verification
arms with no committed transition. Divergences are still tracked separately; a `guard_eq` proves
the model guard, not the deployed guard.

## Guard extraction in practice

For an arm, define a pure guard `g : σ → π → Bool` and an effect `f : σ → π → σ`. Prove:

1. `step s p = some (f s p)` when `g s p`, and `step s p = none` otherwise.
2. A decision table transcribed from the contract's guard, with columns for each status, role,
       proof, and height boundary, agrees with `g` on every row.
3. The deployed suite asserts the same table against the contract, and a vector file records the
       row.

The table is finite and the domains are chosen. The proof must not claim completeness beyond the
table. `native_decide` is forbidden; the tables are small enough for `cases`/`decide` or explicit
rewrites. This is the honest form of “the model matches the code” available without a Rholang
semantics.

## Versioned independence in practice

The current `Store`/`World` layer already has framing and commute theorems. The versioned layer adds
generations and the accepted/rejected/stale outcome. The target is:

- `set_commute` and `commit_commute` for distinct cells;
- a frame theorem that a run on cell `c` leaves every other cell unchanged;
- `runExec_append` and `runExec_commute_distinct` for disjoint footprints;
- a projection theorem that a multi-cell run restricts to each cell's serialized run.

The last theorem is the bridge to `core_races_not_representable`: the headline result is the
per-cell projection of the versioned run, while independence is a separate property of disjoint
footprints. The roadmap does not claim that independence implies global race freedom.

## Proof-cell linearity in practice

`Arm.proofCells` must become a relation, not metadata. The plan:

1. A proof event is an `Event (ProofState α)` on a proof cell, as in `ProofVersioned`.
2. An arm event is related to a proof event by a `Consumes` predicate carrying the proof cell, the
       arm, and the payload.
3. A well-formed arm run requires every declared proof cell to be consumed before the arm's commit,
       exactly once, and no two arms to consume the same proof generation.
4. `core_no_proof_reuse_across_arms` is a trace theorem over the combined event list, not a
       statement about one proof cell in isolation.

This still does not prove that the deployed private capability is unforgeable. It proves the
consumption discipline of the model.

## Invariant coverage after the roadmap

| Invariant | Current | Target |
|---|---|---|
| D1–D3 | proved | proved |
| C1–C2 | partial (guard fidelity) | R2 via LR-01/LR-08 |
| C3 | proved | proved |
| V1–V2 | proved | proved |
| K1–K3 | K1 partial, K3 partial (forest vs tree) | R2 / precise statement |
| O1–O2 | O1 partial (retry window) | R2 / recovery model |
| P1 | partial (creation authenticity) | R2 / explicit advisory boundary |
| L1–L2 | partial (Store only) | versioned via LR-02 |
| L3–L4 | proved-but-narrower (finite static ranks) | unchanged; no scheduler claim |

## What remains unprovable here

No mechanized Rholang semantics, no refinement of the deployed contracts, no proof of name
unforgeability, chain-height authenticity, JSON schema validity, phlo exhaustion, scheduler
fairness, or liveness. A model theorem is never cited as deployed refinement. `proved-conformance`
is finite evidence, not a proof over all inputs.

## Acceptance

- Every deployed mutating arm has an `Arm` value and, when `proved-model`, a `guard_eq` entry or an
  explicit `owed` reason.
- `VWorld` has the commute/frame theorems and the independence alias is no longer a `Store` alias.
- `proofCells` is read by a consumption theorem.
- The pair matrix is complete or every unmodeled pair has a reason.
- `check_lean --audit-coverage`, `check_flows`, `check_race_matrix`, and `check_arm_guards` enforce
  the above; `check_audit --phase2` requires an approved review and no open P0/P1 disposition.
- No `sorry`, `admit`, `native_decide`, or new axiom.
