# Proof audit

This page audits what the Lean theorems actually state and where the model diverges from the
deployed Rholang. The machine-readable record is
[`spec/proofs/rigor.yaml`](https://github.com/rhovision-org/r-gen/blob/main/spec/proofs/rigor.yaml)
and [`spec/audit/findings.yaml`](https://github.com/rhovision-org/r-gen/blob/main/spec/audit/findings.yaml).

## Claim versus theorem

All 39 Pareto theorems have a claim entry. The verdict vocabulary is in the
[audit charter](audit-charter.md). The table below is representative; the full ledger carries the
exact quantifiers, premises, and missing coverage.

| Public claim | Actual theorem | Verdict |
|---|---|---|
| The core is race-free | `core_races_not_representable`: ∀ valid `Run`, ∀ cell, no two same-cell events share an expected generation | proved-but-narrower |
| Every arm decision is authorized by its consumed cell | `core_arm_authority`: the decision function depends only on the cell value | proved-but-narrower |
| Proof payloads are consumed once | `proof_take_once_versioned`: a second take on the same proof cell rejects | proved-but-narrower |
| Independent cells commute | `L1_disjoint_commute` / `commit_commute` on `Store`/`World` | proved-but-narrower |
| Identity update is modeled | `ProfileState.updateProfile` models the deployed profile patch; `updateOwner` remains a separate ownership model | proved |
| Nesting is a forest with strict order | `nest_acyclic` plus order; multiple parents are not excluded | proved-but-narrower |
| Oracle execution is exactly once and subject-bound | `execute_once`; the deployed two-contract retry window is not modeled | proved-but-narrower |
| Provenance is append-only | `anchors_append_only`; creation authenticity is not modeled | proved-but-narrower |

The headline theorem is true and useful. It is **not** a general race-freedom result. It does not
cover cross-cell races, proof reuse across arms, deployed guard equivalence, scheduler/interleaving
semantics, or Rholang capability semantics. The public pages now state that boundary; the theorem
name is retained for compatibility.

`core_arm_authority` means functional dependence, not permission. `Arm.decision` reads only
`w.cell a.cell`. Who may invoke the arm, and which proof it must consume, are guard and operational
concerns. The arm's `proofCells` field is not read by `decision` or `event`; see RGA-002.

## Model-versus-code divergences

Sixteen divergences were recorded with a direction; two are resolved in Phase 2. `model-permissive` means the model admits more
than the contract, so a model invariant may still be conservative but the arm's real guard is
unproved. `model-stricter` and `effect-omitting` mean a model proof may not cover the deployed arm.

| ID | Arm | Direction | Difference |
|---|---|---|---|
| DIV-001 | `Credential.revoke` | mixed | Resolved: model revoke now requires active status |
| DIV-002 | `Credential.prove` | mixed | Resolved: model uses `h <= expiresAt` and no `issuedAt` lower bound |
| DIV-003 | `Credential.renew` | mixed | Model adds `issuedAt <= newExpiry`; deployed writes `evidenceHash` and `renewals` |
| DIV-004 | `KAsset.approve` | model-permissive | Phase 2 requires the Approver credential type; registry/minLevel qualification remains unmodeled |
| DIV-005 | `KAsset.nest` | model-permissive | Resolved: model now requires an approved parent |
| DIV-006 | `KAsset.nest` | mixed | Resolved: model requires strictly increasing `approvedAt` |
| DIV-007 | `Claim.validate` | shape-different | Model takes a caller-chosen K-Asset id; deployed mints with `makeKAsset` |
| DIV-008 | `Claim.validate` | shape-different | Model checks `requirement`; deployed checks `selectionCriteria` |
| DIV-009 | `Oracle.evidence` | model-permissive | Resolved: model requires a listed party or the adjudicator |
| DIV-010 | `VP.proveValidated` | effect-omitting | Model payload lacks `caller` and accepts caller-chosen `atHeight` |
| DIV-011 | `Identity.update` | shape-different | Model transfers ownership; deployed patches profile hashes |
| DIV-012 | `IdentityFactory.create` | effect-omitting | Model proves first-writer-wins only; deployed also writes identity and bundle |
| DIV-013 | `Claim.validate` | shape-different | Deployed Claim and K-Asset verdict mappings disagree on unknown verdicts |
| DIV-014 | `OracleCase.execute` | effect-omitting | Model has no `executing` state or cross-contract retry window |
| DIV-015 | `ProvenanceFactory.create` | effect-omitting | Creation is unauthenticated and chooses the writer list |
| DIV-016 | `KAsset.nest` | shape-different | Deployed uses a peek pre-pass, then consume and recheck; model is one atomic step |

## Assumption ledger

The model assumes, but does not prove: `Run` is a finite trace and not a scheduler; `Event.apply` is
deterministic and pure; names and proof capabilities are unforgeable; heights are authentic; arm
steps are hand-transcribed; proofs are data plus a one-shot cell; phlo, depth, serialization size,
and JSON shape are deployment concerns; model state records only the fields the invariants need.
These assumptions are mirrored in the [formal model](formal-model.md) and the
[race-freedom proof](race-freedom-proof.md).

## Gate audit

| Gate | What it enforces | What it assumes |
|---|---|---|
| `check_lean.py` | No `sorry`/`admit`/`native_decide`; no declared axiom; hand-listed theorems are axiom-clean | The list is complete (RGA-006) |
| `check_flows.py` | Deployed arms appear in the manifest; mapped entries are deployed; named Lean declarations exist | Names are the right declarations; no guard equality |
| `check_race_matrix.py` | Class vocabulary, pair uniqueness, theorem existence | The theorem matches the pair; matrix is not complete (RGA-007) |
| `check_arm_guards.py` | Consumed cell matches the manifest; named transitions, authorities, and `guard_eq` entries exist | The `guard_eq` proves the model guard, not the deployed Rholang guard (RGA-004) |
| `check_pareto.py` | Terms, cells, modules, theorems, docs citations exist and are in `Pareto.lean` | The curated set is minimal and correct |
| `check_audit.py` | This record is internally consistent and traceable to arms, theorems, docs, and actions | The review has not yet approved it |

The devnet and behavioural suites run nightly or manually, not on every pull request (RGA-011).
They are regression evidence, not the proof.

## Findings that need a proof decision

The twelve P0-scored findings are not all proof defects. They are the items that crossed the
rubric’s P0 line at the audit baseline and needed an explicit review decision. The proof-side items
were:

- RGA-002: proof-cell metadata is inert; no cross-arm proof-reuse theorem.
- RGA-003: versioned independence is missing; the L1 alias is a plain-Store theorem.
- RGA-004: guard definitions and `guard_eq` theorems now exist for all 32 mutating proved-model arms; the model/code divergences remain in the ledger.
- RGA-005: `proved-conformance` was zero; all 35 proved arms are now promoted vector-suite pairs.
- RGA-013: `Identity.update` was mapped to a different operation; now modeled by `ProfileState.updateProfile`.

The remaining P0 items are contract-state and atomicity findings: RGA-020 (verdict mapping),
RGA-022 (provenance creation), RGA-023 (oracle open), RGA-024 (oracle execute retry), RGA-031
(identity create), RGA-032 (claim mint), and RGA-033 (nest proof consumption). The complete ranked
list is in the [HAZOP](hazop.md#deviations-that-feed-the-backlog) and the
[improvement plan](rholang-improvements.md).

## Phase 2 progress

The owner authorized Phase 2 with the independence limitation recorded. Since the audit:

- `ProfileState.updateProfile` and an `IdentityPatch` model replace the wrong `Identity.update`
  mapping, and `Identity.update`, `IdentityFactory.create`, and `ValueProposition.comment` have Arm
  values (LR-00, RGA-013, RGA-008).
- 32 core mutating arms have a `guard_eq` theorem and a manifest entry, including identity, credential,
  claim, K-Asset approval/rejection, oracle, and provenance write guards (LR-01).
- `VWorld.set_commute`, `VWorld.commit_commute`, `Event.apply_commute_distinct`, and
  `core_independent_arms_commute` connect the versioned layer to independence (LR-02, LR-04).
- `check_lean.py --audit-coverage` requires every Pareto `#check` in `Audit.lean`; 64 Pareto checks
  and 173 axiom checks pass (LR-07).
- The model-only finish/execute race row is removed and provenance anchor/comment is added; the matrix is 32 rows (LR-05 partial).
- Claim and K-Asset verdict mappings now agree for `valid`, `partial`, `invalid`, and unknown
  verdicts; claim deadline presence and comment-window ordering are checked at creation (RR-04,
  RR-07 partial).

Still open: `proofCells` trace consumption (LR-03), a full `runExec` commute theorem, conformance
promotion (LR-06), the remaining model/code divergences (LR-08), and the three atomicity findings
(RGA-031…033). All 32 mutating proved-model arms have a `guard_eq`; the other three are read-only.

## What would change the verdict

The proof-side verdicts become `proved` for the model only when the corresponding LR item closes.
Even then the result is a model result, not a refinement. The [rigor roadmap](rigor-roadmap.md)
states the ladder and the remaining unprovable boundary.
