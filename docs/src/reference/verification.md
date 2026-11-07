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

## Web client and devnet (2026-11-04)

- `harness/demo_seed.py`: pass on the isolated devnet — identities for issuer/alice/bob/
  carol/dave, three credentials, a value proposition, an approved claim/K-Asset, a disputed
  and upheld claim/K-Asset, an oracle case with decision and execution, and provenance with
  two anchors and a comment.
- `harness/demo_verify.py`: 14 catalogue entries verified; identity directory lookups,
  factory `verify` calls, and the claim ↔ K-Asset ↔ case ↔ provenance relationships checked
  in both directions.
- `harness/unit_all`: ten behavioural suites pass after rebuilding the contracts.
- `web`: Vitest 11/11; offline WASM smoke (wallet create/unlock/export, BLAKE2b-256, claim
  payload validation); TypeScript strict build; Playwright read journey and full
  claim → validation → approval handshake against the seeded devnet.
- Browser journey exercised manually with real keystores: wallet create, faucet, identity,
  claim, validation, K-Asset approval, dispute → decide → execute, provenance anchor and
  verify. Every action waited for finality and the entity was re-read.
- Oracle `open` regression fixed: the Phase 2 guard checked `caseReq.subjectRef`, which the
  K-Asset/VP dispute arms never set. It now checks the `subjectRef` argument. This restored
  the dispute path that `unit_core` exercises.

## Lean model (2026-11-07)

- `cd spec/lean && lake build`: 45 Lean files build on Lean `v4.12.0`, no Mathlib.
- `tools/check_lean.py`: 45 files, no `sorry`, `admit`, `native_decide`, or declared
  axioms.
- `tools/check_lean.py --audit`: the 241 theorems listed in `RGen/Audit.lean`, only
  `propext` and `Quot.sound`; no `Classical.choice` use in the audited set. The list is
  hand-maintained (RGA-006).
- `tools/check_lean.py --audit-coverage`: 129 Pareto theorem checks are covered by
  `Audit.lean`.
- `tools/check_core_vectors.py`: 46 emitted rows match `spec/vectors/core.tsv`.
- New composed results: `RGen/Model/IdentityReservation.lean`,
  `RGen/Model/ClaimMint.lean`, `RGen/Model/ProofCapability.lean`,
  `RGen/Model/NestCrash.lean`, `RGen/Deadline.lean`, `RGen/System.lean`, plus the
  proof-token extension in `Linear/Consumption.lean` and the run-framing aliases in
  `Linear/Exec.lean`. The headline theorems are
  `ReservedDirectory.at_most_one_identity_per_address`,
  `ClaimMintState.at_most_one_reachable_kasset_per_claim`,
  `ProofCap.private_capability_no_bearer_dos`, `crash_release_all`,
  `deadline_boundary_deterministic`, `system_safety`, and
  `core_no_proof_reuse_across_arms`.
- `tools/check_flows.py`: 67 deployed arms mapped — 0 `proved-model`, 35
  `proved-conformance`, 32 `owed` (read-only arms, creation registries, and extensions).
  The former phantom `Issuer.revoke` entry is removed. `Identity.update`,
  `IdentityFactory.create`, and `ValueProposition.comment` now have Arm values.
- `tools/check_race_matrix.py`: 32 pairs (19 exclusive, 11 ordered, 2 independent).
- `tools/check_arm_guards.py`: the mutating arms are tied to a consumed cell.
- `tools/check_audit.py --strict`: 67 arms dispositioned, 10 HAZOP nodes, 150 coverage cells,
  146 rows, 45 claims, 62 findings, 13 Rholang items. Review status is `approved` by the owner; independent technical review has not been performed. The reviewed
  pages start at the [audit charter](audit-charter.md); the findings are in
  [`spec/audit/findings.yaml`](https://github.com/rhovision-org/r-gen/blob/main/spec/audit/findings.yaml).

The model proves `run_frame`, `run_agree`, `disjoint_cells_commute`,
`disjoint_cells_commute_wf`, the three commit lemmas, D1–D3, the versioned no-same-
generation theorem `core_races_not_representable`, the arm authority theorem
`core_arm_authority`, and the 32-pair race matrix in `spec/flows/races.yaml`. The
behavioural race suite is regression evidence only; it is not the proof. It is a model
proof: no mechanized Rholang semantics and no refinement theorem.

## Local-devnet test tiers (2026-11-07)

- `make devnet-test-smoke` — preflight, install, `devnet-verify`, identity/credentials/claim.
- `make devnet-test-full` — smoke + all ten suites, red team, capability red team,
  deploy-semantics probe, demo seed/verify, web tests and both Playwright journeys,
  `make check`, `make lean-check`.
- `make devnet-test-nightly` — full + reinstall check + 20-deploy soak; fault injection is
  recorded as skipped until the recovery harness lands.
- `make devnet-verify` resolves all nine Root keys through the deployed manifest and exits 4 on
  a missing key or URI mismatch.
- The full plan and the P1/P2 gap list are in [Local-devnet testing](../guides/devnet-testing.md).

## HAZOP, red team and deploy semantics (2026-11-07)

- Blind multi-agent workflow HAZOP: 25 rows over 9 workflow/cross-node nodes; every S1/S2 row
  has two authors or an adjudication decision. `tools/check_hazop_runs.py` passes. The 146-row
  contract worksheet remains the prior register; the new run is in
  `spec/hazop/runs/2026-11-07/`.
- `harness/probe_deploy_semantics.py`: a reduction error rolls back; a blocked continuation
  commits the consumed cell. The reachable partial-commit path is a non-replying callee, not an
  erroring deploy.
- `harness/redteam_core.py`: RT-004 proof-URI theft, RT-006 Nil comment, RT-007 subjectRef,
  RT-008 credential fields, RT-009 oracle past deadline, RT-020 VP validator dispute, RT-021 VP
  late validation, RT-022 oracle late decision, and RT-023 credential attribution are fixed.
  RT-011 provenance spoofing, RT-012 execute crank, and RT-013 permissionless proof minting are
  accepted with reasons. RT-001 duplicate identity was not reproduced; the reservation protocol
  removes the window.
- `make guard-check`: 16 changed arms; source atoms and flow entries agree. Six arms have an
  `owed` guard_eq and are reported as warnings, not passes.
- `make style-check`: 68 `if` / 102 `match`; 0 errors and `passes: true`. Every `else if`,
  branch-only boolean channel, index-recursive list walk and match deeper than dispatch depth 2
  is gone. `List.rho` is list-pattern recursion; `KAsset.rho` is fully flat helper chains. The
  inventory is `spec/audit/rholang-control-flow.yaml`.

## Object-capability audit (2026-11-07)

- `spec/audit/capabilities.yaml`: 38 capability rows over 19 `bundle+` expressions, 3 proof
  kinds, 2 private `Apply` capabilities, 7 ambient system channels. `tools/check_capabilities.py`
  checks the register against the source and passes with 0 errors.
- `harness/redteam_capabilities.py`: RT-024..RT-037. Pre-fix RT-031 (`Issuer.authorize` with a
  caller-nominated address) and RT-032 (self-registered fake child nested under a real parent)
  were observed `vulnerable`; RT-036 (validator dispute) and RT-037 (malformed `dId` in
  Root.register) were source-identified and are post-fix regression probes. Post-fix the suite
  is `RGEN_EXPECT=fixed` green: RT-031/032/036/037 `fixed`, the rest `accepted`.
- Blind run `spec/hazop/runs/2026-11-07-capabilities/`: 36 rows over 9 capability nodes,
  18 adjudication decisions. `tools/check_hazop_runs.py` validates both runs.
- Fixed: K-Asset child anchor (RGA-049), Root register state order (RGA-061), `Issuer.authorize`
  caller derivation (RGA-048), K-Asset validator dispute parties (RGA-060), K-Asset reply
  bundle (RGA-050), issuer registry hold (RGA-069), installer Root check and dry-run guard
  (RGA-058/059), client cache refresh and resolve-all wording (RGA-056/057).
- Accepted with the reasons in the register and adjudication: proof bearer burn, permissionless
  `proveApproved`/`execute`, durable approval and validation across credential revocation,
  forest nesting, disputed-asset freeze on an expired case, provenance writer immutability,
  unsigned manifest Root designation, and `dId` delegation.
- Lean: `RGen.Model.Capability` adds 8 theorems; `make lean-check` reports 45 files, 241
  axiom-clean theorems and 129 Pareto checks. The model is abstract; name unforgeability is
  ASM-003/ASM-011, not a theorem.

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
make unit-all
make demo-seed demo-verify

npm --prefix web ci
npm --prefix web run test:wasm
npm --prefix web test
npm --prefix web run typecheck
npm --prefix web run build
RGEN_E2E=1 npm --prefix web run test:e2e
```

**Honest limit:** the core has two behavioural suites (vertical slice and race suite). The
extension suites (receipt, payments, risk, panels) are not implemented in this tree.
