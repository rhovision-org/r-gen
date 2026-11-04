# Status and limits

**Devnet-only, no real value. Phase 1 audit recorded; Phase 2 partial; Phase 3 pending; independent review pending.**

## Verified on 2026-11-04

- 7 core deploy terms, 16 catalogue components, 10 state cells, acyclic.
- All 7 rendered terms parse with the pinned rholo parser.
- `harness/unit_core.py`: pass — identity → credential → value proposition → claim →
  validation → K-Asset → approval → dispute → oracle → provenance.
- Ten behavioural suites pass: identity, credentials, claim, K-asset, value, oracle,
  provenance, integration, vertical slice, and behavioural race regression.
- Lean proof gates: 37 files, no `sorry`/axiom; the 194 theorems listed in `Audit.lean`
  are axiom-clean (`propext`, `Quot.sound` only); `core_races_not_representable`; 32-pair
  race matrix; 9 `proved-conformance` arms. The audit list is hand-maintained (RGA-006).
- Static gates: build, parse, arch, captures, placeholders, money, core boundary,
  concurrency, citations, flows, race matrix, arm guards, audit.
- Phase 1 audit: 65 deployed arms dispositioned; 10 HAZOP nodes, 150 coverage cells, 146 rows;
  27 findings (12 P0, 13 P1, 2 P2; no S1); 39 Pareto claim entries; 11 Rholang items and 9 Lean
  items. The record is in `spec/audit`, `spec/hazop`, `spec/proofs`, and `spec/improvements`.

## Core boundaries

The core installs only: Root, Identity, Issuer/Credential, Claim/K-Asset, ValueProposition,
Oracle, Provenance. It does **not** install KAT, payments, risk scoring, panels, admin,
handles, metrics, or a web client.

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
