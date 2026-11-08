# Improvement plan

`spec/audit/improvement-plan.yaml` is the risk/effort portfolio that follows the P0/P1
close-out. It is checked by `tools/check_improvement_plan.py` (`make
check-improvement-plan`) and included in `make spec-check`.

**This is not the Pareto core ledger.** The primitive-minimality filter lives in
[the Pareto ledger](pareto-ledger.md) and `spec/pareto.yaml`; it is unchanged. This page
uses "Pareto" in the risk/effort sense: schedule the work that removes the most residual
risk per unit of implementation and verification effort.

## Scoring

Each item records:

- **risk reduction (1–5):** 5 = S1/P0 residual or repeatable state-integrity/authority
  failure; 4 = S2/risk 9; 3 = liveness/policy; 2 = proof/claim/operational gap; 1 = wording;
- **effort (1–5):** 1 = docs/config; 2 = a test, tool or single-arm change; 3 = a new
  transition or multi-file install/client change; 4 = protocol change with a Lean proof or
  signing/key management; 5 = cross-system governance;
- **confidence:** high (mechanically checked), medium (tested, not modeled), low
  (judgement only).

The checker computes `score = risk / effort` and validates the frontier **per class**.
Global dominance across unrelated classes is misleading: an E1 registry fix must not
"dominate" independent proof or supply-chain work. Classes are `live-risk`, `assurance`,
`ops`, `proof-debt`, `supply-chain`, `hygiene`, and `policy`.

## Tiers

### Tier 0 — make the plan auditable and start the S1 review

- **IMP-011** Prepare and commission the external S1 review packet. The review itself is
  an external prerequisite; the packet assembles the close-out, the manifest-substitution
  and oracle-wiring traces, and the red-team results.
- **IMP-012** Fail the close-out gate on a code-only S1 fixed row. The strict S1 mode is
  cheap and prevents the S1 evidence from regressing to a code-only claim.

### Tier 1 — live-risk and supply chain

- **IMP-001** Install plan with kind-bound verification, atomic manifest and resumable
  state. This replaces six install/HAZOP patches with three coherent units: install
  identity, wiring verification, and partial-install recovery. It includes the RGA-070
  wrong-oracle negative test.
- **IMP-002** Refuse duplicate keys in factory registries.
- **IMP-003** Bind every registry `verify` to the record URI and kind, and add the
  registry-trust static gate. This covers RGA-053's consumer-side risk.
- **IMP-004** Enforce Root pinning by default for non-devnet profiles. This is the cheap
  80% fix for the S1 manifest finding; signed manifests stay in Tier 3.
- **IMP-005** Add dependabot, `cargo audit`, hashed Python requirements, and the web dev
  dependency upgrade.
- **IMP-015** Complete the identity-create recovery record (RR-11), the last accepted
  cross-cell atomicity window.

### Tier 2 — bounded follow-ups

- **IMP-006** Increment `execution.attempts` and add `OracleCase.abandon` (RGA-071,
  WF-011/012).
- **IMP-007** Fault-inject between receipt and commit for nest and mint (RGA-033/065).
- **IMP-008** Separate installer and Issuer keys and drill key-loss recovery (RGA-052).
- **IMP-009** Triage DIV-001..016 with an explicit status and justification (RGA-004/LR-08).
- **IMP-010** Sync the stale status, acceptance, measure and wording artifacts (RGA-030,
  PRF wording).

### Tier 3 — deferred, with a reason

- **IMP-013** Signed manifest with a distributed trust root; deferred because enforced
  pinning covers the default build at lower effort.
- **IMP-014** Close the remaining proof debt (LR-01, LR-08 closure, RGA-006/007).
- **IMP-016** Complete or justify the 16 unrecorded race pairs (RGA-007/LR-05).
- **IMP-017** Decide the de-approval, devalidation, writer-removal and caller-bound
  policies (RGA-055/062/063/066/040/054).
- **IMP-018** Revisit the registry cap and PR devnet tier when infrastructure allows
  (RGA-029/011).

## Relationship to the close-out

The close-out ledger answers "is it closed?"; this plan answers "what next, in what
order?" The checker never changes a close-out decision. When work lands, update both in
one change and cite overlapping evidence. An expired risk acceptance still fails
`make check-closeout`, whether or not it has a scheduled improvement.

## Gates

`make check-improvement-plan` checks the plan's IDs, ranges, computed scores, coverage of
every S1 acceptance and every partial RR/LR item, and class-aware dominance. The plan is
a decision record, not a second findings ledger.
