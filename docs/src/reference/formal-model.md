# Formal model

The Lean model is in `spec/lean/`. It is built with Lean `v4.12.0`, no Mathlib, no
external `require`. `make lean-check` builds it, rejects `sorry`/`admit`/`native_decide`
and declared axioms, audits the public theorems, and checks the emitted corpus.

## What is proved

Lean proves properties of **the model**, not of the deployed Rholang. There is no
mechanized Rholang semantics and no refinement theorem. The flow manifest and the
conformance corpus are traceability, not refinement. This is the same boundary r-cash
and r-share draw around `proved-model`.

## Module map

| Module | Contents |
|---|---|
| `RGen.Basic` | heights, ids, requirement/scope/issuer-scope, `scopeMatches`, `issuerCovers`, lexicographic order |
| `RGen.Linear.Cell` | `Store`/`run`, D1–D3, footprints, framing, independent-trace commutation, `World`/`commit` |
| `RGen.Linear.Protocol` | generic `Step`, `Reach`, invariant induction, `Terminal` |
| `RGen.Linear.Versioned` | versioned cells, atomic commit, take/post, `take_take_blocks`, `take_post_commit_equiv` |
| `RGen.Linear.Exec` | `Event`, `Run`, `runExec`, projection, `runExec_no_same_expected` |
| `RGen.Linear.Authority` | `DependsOnlyOn`, `FactorsThroughCell`, `cross_cell_read_not_authority` |
| `RGen.Linear.Lift` | `Arm`, `decision`, authority lift |
| `RGen.Model.ProofVersioned` | one-shot proof take in the versioned model |
| `RGen.Arms.*` | per-primitive pair theorems |
| `RGen.Arms.Instances` | concrete core `Arm` values and authority instantiations |
| `RGen.ArmGuards` | guard definitions and `guard_eq` theorems for the core arms |
| `RGen.Pareto` | curated Pareto theorem vocabulary |
| `RGen.RaceFreedom` | headline non-representability theorems |
| `RGen.Model.Proof` | one-shot proof cells with an arbitrary payload, `ProofData` |
| `RGen.Model.Registry` | append-only registry, monotone `verify`, duplicate refusal |
| `RGen.Model.Identity` | first-writer-wins directory, owner-only transfer |
| `RGen.Model.Issuer` | immutable issuer; the transition relation has no constructors |
| `RGen.Model.Credential` | active/revoked, prove guard, revoke/renew/attest, identity invariance over `Reach` |
| `RGen.Model.ValueProposition` | proposed → validated → disputed → upheld/revoked; one-shot validated proof |
| `RGen.Model.Claim` | open → validated/rejected/withdrawn/expired; exactly one K-Asset reference |
| `RGen.Model.KAsset` | approve with credential+VP proofs, two-phase nest, dispute, approval proof |
| `RGen.Model.Oracle` | decide with the stored adjudicator credential, subject-bound one-shot execute, close |
| `RGen.Model.Provenance` | append-only anchors and comments, monotone verify |
| `RGen.Concurrency` | cell ranks, `MayAcquire`, acyclicity, rank deadlock-freedom |
| `RGen.Composition` | composed guarantees across primitives |
| `RGen.Invariants` | stable names `D1`–`D3`, `C*`, `V*`, `K*`, `O*`, `P*`, `L1`–`L4` |
| `RGen.Emit` | emits `spec/vectors/core.tsv` |
| `RGen.Audit` | `#print axioms` for the public theorems |

## Cell semantics

`Store α` maps a `CellId` to a list. `run` interprets `peek`, `take`, `put`, `call`, and
`commit`. `take` requires a singleton and records the cell as held; `put` requires the
cell empty and held, then erases one occurrence from the held list; `call` is refused on
a held cell; `commit` is one atomic read-modify-write and never exposes an empty cell.

The held list records a take by consing without deduplicating. Held agreement is
therefore stated as per-cell occurrence counts (`occ`), which `take`/`put` preserve;
plain membership is not preserved by `put` when the initial held list has duplicates.

`World α` maps a cell to `Option α` and is the application-level concurrency model:
`commit_commute`, `commit_same_cell`, and `commit_preserves_other` are the three commit
lemmas used by the entity proofs.

## Per-primitive guarantees

Representative public names (the full list is `RGen/Audit.lean`):

- **Credential**: `prove_requires_subject`, `prove_requires_active`,
  `prove_requires_scope`, `prove_snapshot`, `prove_after_revoke`,
  `prove_wrong_subject`, `credReach_preserves_identity`.
- **Value proposition**: `validate_once`, `proveValidated_requires_validated`,
  `prove_after_dispute`, `dispute_once`, `terminal_no_transition`.
- **Claim**: `validate_requires_open`, `validate_requires_non_claimant`,
  `validate_within_deadline`, `validate_once`, `validate_sets_kasset`,
  `validate_creates_exactly_one_kasset`, `terminal_no_transition`.
- **K-Asset**: `approve_only_from_validated_or_conditional`,
  `approve_requires_credential_proof`, `approve_requires_vp_proof`,
  `approve_by_claimant_refused`, `nest_requires_order`, `nest_refused_unsorted`,
  `nest_acyclic`, `proveApproved_requires_approved`, `approvedAt_stable`.
- **Oracle**: `decide_requires_adjudicator`, `decide_requires_proof`, `decide_once`,
  `execute_subject_bound`, `execute_once`, `close_requires_finished`,
  `close_open_refused`.
- **Provenance**: `anchors_append_only`, `anchor_unique`, `verify_monotone`,
  `addComment_requires_writer`.

## One-shot proofs

`ProofState α` is `{ data : α, used : Bool }`. `take` returns the payload and marks the
cell used; `take_second` and `take_take` show a second take fails; `take_data` shows the
payload is a snapshot. The `used` flag is observability and testability, not the security
boundary: the capability is private and unforgeable in the deployed model.

Credential, value-proposition, and K-Asset proofs use the same cell. Revocation and
dispute after a proof are non-retroactive by construction: the proof carries a snapshot
of the pre-state.

## Axiom audit

`tools/check_lean.py --audit` elaborates `RGen/Audit.lean`. On 2026-11-04 the listed
192 theorems reported only `propext` and `Quot.sound` (`Classical.choice` is permitted
but unused). The list is hand-maintained; the [proof audit](proof-audit.md) records that
gap as RGA-006.

## Manifest and corpus

`spec/flows/core.yaml` maps every deployed arm to a Lean declaration and one of four
statuses: `proved-model`, `proved-conformance`, `owed`, `open`. At this checkpoint 34
of the 65 deployed arms are `proved-model`, 1 is `proved-conformance`, and 30 are `owed`
(read-only arms, creation registries, and extensions). `Identity.update` is modeled by
`ProfileState.updateProfile`. `tools/check_flows.py` enforces coverage, deployment, and
declaration existence.

`spec/vectors/core.tsv` is emitted by `lake exe emit` from `RGen/Emit.lean`.
`tools/gen_vectors.py --write` refreshes it; `tools/check_core_vectors.py` rejects drift.
`proved-conformance` is claimed only for a row that is both emitted and asserted by a
suite; credential prove, VP validate, and VP proveValidated are claimed through the emitted vectors and `unit_credentials.py` / `unit_value.py`.

## Honest limits

- The deployed contracts use the proof-URI design and the reconciled guards; the race
  proof is `core_races_not_representable`. The arm-to-model map is hand-transcribed, not a
  refinement.
- `deadlock_free_of_rank` is a lock-order theorem under finite cells and no dynamic
  locks. It is not global scheduler liveness or starvation freedom.
- Race freedom is structural: proof issuance is the linearization point. The model does
  not enumerate interleavings.
- The `nest` pre-pass in the contract is a hint; the child proof is the authority. The
  model has no `KAsset → KAsset` acquisition edge.
