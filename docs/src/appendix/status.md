# Status and limits

**Devnet-only, unaudited, no real value.**

## Verified on 2026-11-04

- 7 core deploy terms, 16 catalogue components, 10 state cells, acyclic.
- All 7 rendered terms parse with the pinned rholo parser.
- `harness/unit_core.py`: pass — identity → credential → value proposition → claim →
  validation → K-Asset → approval → dispute → oracle → provenance.
- `harness/concurrency_core.py`: pass — one of two validations wins; one of two approvals
  wins; exactly one oracle apply; cross-subject isolation; two comments both stored; eight
  independent claims validate in one deploy; a revoked credential refuses.
- Static gates: build, parse, arch, captures, placeholders, money, core boundary,
  concurrency, citations.

## Core boundaries

The core installs only: Root, Identity, Issuer/Credential, Claim/K-Asset, ValueProposition,
Oracle, Provenance. It does **not** install KAT, payments, risk scoring, panels, admin,
handles, metrics, or a web client.

## Owed

- Extension suites: receipt/KAT, payments/r-cash, risk/SPE, panels, governance, metrics.
- A broader core suite set (the current tree has the vertical slice and the race suite).
- Lean models and a flow-to-theorem map.
- A public-release paper profile that replaces non-redistributable PDFs with links.

## Honest limits

- "Maximal concurrency" means no shared mutable cell across independent entities and one
  writer per entity. It is not an absolute optimality theorem.
- Identity creation and credential issuance are deliberate serialization points; neither is
  on the claim/validation hot path.
- Oracle selection is deterministic and named by the parties, not a random beacon.
- Nesting uses a strict `(approvedAt, id)` order; a later-approved child cannot be nested
  into an older parent.
- The papers are third-party copyrighted works and are not AGPL; see `docs/papers/README.md`.
