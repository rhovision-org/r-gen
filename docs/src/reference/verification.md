# Verification record

**Date:** 2026-11-04
**Node:** rholo `e2d073dcd02f1e560ccb84749937138a1e184b0b`
**Devnet:** isolated `rgen-bootstrap` on 40403/40405/40402 (8 GB), existing networks untouched
**Core:** 7 deploy terms, 16 catalogue components, 10 state cells

## Passed

- `tools/build_contracts.py --check`: 7 terms, no drift.
- `tools/parse_check.sh` on all rendered core terms: 7/7 OK.
- `tools/check_arch.py`: 16 components, 10 state cells, acyclic.
- `tools/check_captures.py`, `check_placeholders.py`, `check_money.py`: pass.
- `harness/unit_core.py`: pass — identity → credential → value proposition → claim →
  validation → K-Asset → approval → dispute → oracle → provenance.
- `harness/concurrency_core.py`: pass — one of two validations wins; one of two approvals
  wins; exactly one oracle apply; cross-subject isolation; two comments both stored; eight
  independent claims validate in one deploy; a revoked credential refuses.

## Lean model (2026-11-04)

- `cd spec/lean && lake build`: 36 Lean files build on Lean `v4.12.0`, no Mathlib.
- `tools/check_lean.py`: 37 files, no `sorry`, `admit`, `native_decide`, or declared
  axioms.
- `tools/check_lean.py --audit`: the 194 theorems listed in `RGen/Audit.lean`, only
  `propext` and `Quot.sound`; no `Classical.choice` use in the audited set. The list is
  hand-maintained (RGA-006).
- `tools/check_core_vectors.py`: 44 emitted rows match `spec/vectors/core.tsv`.
- `tools/check_flows.py`: 65 deployed arms mapped — 2 `proved-model`, 33
  `proved-conformance`, 30 `owed` (read-only arms, creation registries, and extensions).
  The former phantom `Issuer.revoke` entry is removed. `Identity.update`,
  `IdentityFactory.create`, and `ValueProposition.comment` now have Arm values.
- `tools/check_race_matrix.py`: 32 pairs (19 exclusive, 11 ordered, 2 independent).
- `tools/check_arm_guards.py`: the mutating arms are tied to a consumed cell.
- `tools/check_audit.py --strict`: 65 arms dispositioned, 10 HAZOP nodes, 150 coverage cells,
  146 rows, 39 claims, 27 findings, 11 Rholang items. Review status is `approved` by the owner; independent technical review has not been performed. The reviewed
  pages start at the [audit charter](audit-charter.md); the findings are in
  [`spec/audit/findings.yaml`](https://github.com/rhovision-org/r-gen/blob/main/spec/audit/findings.yaml).

The model proves `run_frame`, `run_agree`, `disjoint_cells_commute`,
`disjoint_cells_commute_wf`, the three commit lemmas, D1–D3, the versioned no-same-
generation theorem `core_races_not_representable`, the arm authority theorem
`core_arm_authority`, and the 32-pair race matrix in `spec/flows/races.yaml`. The
behavioural race suite is regression evidence only; it is not the proof. It is a model
proof: no mechanized Rholang semantics and no refinement theorem.

## Baseline

The pre-Pareto 12-term prototype is on tag `legacy-2026-11-04`; its 12/12 suite result is
the baseline, not the target. The core does not install KAT, payments, risk, panels,
admin, handles, or metrics; those are extensions.

## Reproduce

```sh
make venv
make lean-check
make build-check parse-check
make check-core-boundary check-concurrency check-citations check-flows check-audit
make install
make unit-core
make unit-race
```

**Honest limit:** the core has two behavioural suites (vertical slice and race suite). The
extension suites (receipt, payments, risk, panels) are not implemented in this tree.
