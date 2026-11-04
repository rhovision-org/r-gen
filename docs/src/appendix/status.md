# Status and limits

**Devnet-only, unaudited, no real value.**

## Verified on 2026-11-04

- 7 core deploy terms, 16 catalogue components, 10 state cells, acyclic.
- All 7 rendered terms parse with the pinned rholo parser.
- `harness/unit_core.py`: pass — identity → credential → value proposition → claim →
  validation → K-Asset → approval → dispute → oracle → provenance.
- Ten behavioural suites pass: identity, credentials, claim, K-asset, value, oracle,
  provenance, integration, vertical slice, and behavioural race regression.
- Lean proof gates: 36 files, no `sorry`/axiom; 131 public theorems audited
  (`propext`, `Quot.sound` only); `core_races_not_representable`; 32-pair race matrix;
  no `proved-conformance` claim.
- Static gates: build, parse, arch, captures, placeholders, money, core boundary,
  concurrency, citations, flows, race matrix, arm guards.

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
  mechanized Rholang semantics. The behavioural suites are regression evidence.
- The papers are third-party copyrighted works and are not AGPL; see `docs/papers/README.md`.
