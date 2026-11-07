# Status and limits

**Devnet-only, no real value. Phase 1 audit recorded; Phase 2 and Phase 3 repair in progress; independent review pending.**

## Verified on 2026-11-07

- Contracts hardened for the workflow HAZOP: identity reservation and subject-only resume; claim
  write-ahead validating receipt and resume; private proof capabilities; VP validator-dispute
  auth; VP and oracle deadline guards; claim credential attribution; Nil comment window;
  credential field validation; claim `subjectRef`; provenance creator-in-writers; identity
  update preserves omitted fields; oracle `execute` retries an `executing` case.
- Ten behavioural suites pass after reinstall: identity, credentials, claim, K-asset, value,
  oracle, provenance, integration, vertical slice, and behavioural race regression.
- Lean: 45 files, no `sorry`/axiom; 241 audited theorems axiom-clean; 129 Pareto checks covered;
  the new identity, claim-mint, proof-capability, nest-crash, deadline and composed-system
  modules build.
- Deploy-semantics probe: reduction errors roll back; a blocked continuation commits the
  consumed cell. Cross-cell fixes therefore release the cell before the callee.
- Red team: RT-004/006/007/008/009/020/021/022/023 fixed; RT-011/012/013 accepted with reasons;
  RT-001 not reproduced but removed by the reservation protocol.
- Workflow HAZOP: 25 rows over 9 nodes; `tools/check_hazop_runs.py` passes. The contract-node
  worksheet remains 146 rows.
- Guard bridge: 16 changed arms; source atoms and flow entries agree; six `owed` guard_eq
  warnings.
- Rholang control-flow audit: 68 `if` / 102 `match`, **0 errors**, `passes: true`. Every
  `else if`, branch-only boolean channel, index-recursive list walk and match deeper than
  dispatch depth 2 is gone. `List.rho` is list-pattern recursion; `KAsset.rho` is fully flat
  helper chains; the strict gate is `make style-check`. The inventory is
  `spec/audit/rholang-control-flow.yaml`.

## Verified on 2026-11-04

- 7 core deploy terms, 16 catalogue components, 10 state cells, acyclic.
- All 7 rendered terms parse with the pinned rholo parser.
- `harness/unit_core.py`: pass — identity → credential → value proposition → claim →
  validation → K-Asset → approval → dispute → oracle → provenance.
- Ten behavioural suites pass: identity, credentials, claim, K-asset, value, oracle,
  provenance, integration, vertical slice, and behavioural race regression.
- Lean proof gates: 37 files, no `sorry`/axiom; the 196 theorems listed in `Audit.lean`
  are axiom-clean (`propext`, `Quot.sound` only); `core_races_not_representable`; 32-pair
  race matrix; 35 `proved-conformance` arms. The audit list is hand-maintained (RGA-006).
- Static gates: build, parse, arch, captures, placeholders, money, core boundary,
  concurrency, citations, flows, race matrix, arm guards, audit.
- Phase 1 audit: 67 deployed arms dispositioned; 10 HAZOP nodes, 150 coverage cells, 146 rows;
  62 findings (current priority split in spec/audit/findings.yaml); 45 Pareto claim entries; 13 Rholang items and 9 Lean
  items. The record is in `spec/audit`, `spec/hazop`, `spec/proofs`, and `spec/improvements`.
- Oracle `open` now checks the `subjectRef` argument, not `caseReq.subjectRef`. The Phase 2
  check had made every K-Asset/VP `openDispute` refuse with `case fields`; `unit_core` now
  reaches dispute, decision, execution and provenance on the rebuilt contracts.

## Object-capability audit (2026-11-07)

- Register `spec/audit/capabilities.yaml`: 38 rows over 19 `bundle+` expressions, 3 proof
  kinds, 2 private `Apply` capabilities and 7 ambient system channels; `make
  capabilities-check` passes.
- Live suite `harness/redteam_capabilities.py`: 12 probes (RT-024..RT-037). RT-031/032 were
  observed `vulnerable` pre-fix; RT-036/037 are source-identified post-fix regressions; all
  four are `fixed` and the rest are `accepted`. `make redteam-capabilities` is green under
  `RGEN_EXPECT=fixed`.
- Blind HAZOP `spec/hazop/runs/2026-11-07-capabilities/`: 36 rows, 9 nodes, 18 adjudication
  decisions; `make hazop-check` validates both runs.
- Fixed: K-Asset child anchor (RGA-049), Root register state order (RGA-061),
  `Issuer.authorize` caller derivation (RGA-048), K-Asset validator dispute parties (RGA-060),
  K-Asset reply bundle (RGA-050), issuer registry hold (RGA-069), installer Root check and
  dry-run guard (RGA-058/059), client cache refresh and resolve-all wording (RGA-056/057).
- Lean: `RGen.Model.Capability` adds 8 theorems; 45 files, 241 axiom-clean theorems, 129 Pareto
  checks. The model is abstract and does not prove name unforgeability.

## Web client

- `web/` is a React/Vite/TypeScript reference client over `rgen-wasm`. It reads the deployed
  contracts and signs real deploys; there is no backend and no mock data.
- Routes cover claims, K-Assets, credentials, value propositions, oracle cases, provenance,
  identity, activity and settings. There is no indexer: lists are the local journal, pasted
  share links and the seeded catalogue, and every detail page re-reads its entity.
- A local devnet is one command (`make setup`); the public testnet is opt-in
  (`TESTNET_ALLOW=--allow-live`). The testnet profile pins network id
  `testnet-133b1d307b175012`, shard `/testnet` and the genesis hash.
- On 2026-11-04 the UI was exercised end to end on the isolated devnet: wallet create,
  faucet, identity, claim, validation, K-Asset approval, dispute/decide/execute, provenance
  anchor and verify. Each action waited for finality and the entity was re-read.

## Core boundaries

The core installs only: Root, Identity, Issuer/Credential, Claim/K-Asset, ValueProposition,
Oracle, Provenance. It does **not** install KAT, payments, risk scoring, panels, admin,
handles, or metrics. The web client is a reference consumer of the core, not part of the
installed contract set.

## Owed

- Extension suites: receipt/KAT, payments/r-cash, risk/SPE, panels, governance, metrics.
- A mechanized Rholang refinement; the current proof is model-level with a hand-encoded
  arm map.

## Honest limits

- "Maximal concurrency" means no shared mutable cell across independent entities and one
  writer per entity. It is not an absolute optimality theorem.
- Identity creation and credential issuance are deliberate serialization points; neither is
  on the claim/validation hot path.
- Oracle selection is deterministic and named by the parties, not a random beacon.
- Nesting uses a strict `(approvedAt, id)` order; a later-approved child cannot be nested
  into an older parent.
- Race freedom is proved for the Lean model (`core_races_not_representable`), not for a
  mechanized Rholang semantics. The behavioural suites are regression evidence. The theorem is
  per-cell and per-valid-trace; see the [proof audit](../reference/proof-audit.md).
- The Phase 1 audit found no S1, but it did find material P0-scored state-integrity and
  proof-coverage gaps. They are not fixed yet: Phase 2 requires an approved review. See the
  [HAZOP](../reference/hazop.md) and the [Rholang plan](../reference/rholang-improvements.md).
- The papers are third-party copyrighted works and are not AGPL; see `docs/papers/README.md`.
