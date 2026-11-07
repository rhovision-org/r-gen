# r-gen engineering rules

Binding for humans and agents. If a rule conflicts with convenience, the rule wins.

## Authority order

1. The deployed Rholang in `contracts/src/deploy/` and `contracts/src/lib/` is the
   implementation.
2. `docs/src/reference/pareto-ledger.md` is the primitive/necessity contract.
3. `docs/src/reference/design-rationale.md` is the concurrency/citation contract.
4. The papers in `docs/papers/` are cited source material; they are not the software license.

## Pareto core boundary

The default install is exactly the 7 terms in `harness/install.py`:
Root, Identity, Credential, Claim/K-Asset, ValueProposition, Oracle, Provenance.

The core may **not** reference tokenisation, KAT, mint, payments, risk, panels, admin,
handles, metrics, or any `component:` extension URI. `tools/check_core_boundary.py`
enforces this. Extensions may read core facts by URI/capability; the core never calls an
extension.

## Concurrency rules (non-negotiable)

- Every entity is a factory-created **linear cell** with one writer.
- Every mutating arm consumes first: `for (@s <- state)`, then all guards, then exactly one
  `state!(s')` on every path.
- Read-only arms use `for (@s <<- state)`.
- Never mix `<-` and `<<-` on the same cell in the same arm.
- Never hold a consumed cell across a cross-contract call unless the call graph edge is in
  the documented acyclic list in `design-rationale.md`. The only edges are:
  Claim.validate -> new K-Asset; K-Asset.openDispute -> new Oracle case; Oracle.execute ->
  subject private apply. There is no reverse edge.
- Never store a name in a state map. Capabilities live in process closures.
- Private capabilities (`Apply`) are never published in a bundle.
- No global nonce cell. IDs are registry URIs; uniqueness is the registry's.
- The only serialization points are identity creation (`directoryState`) and credential
  issuance (`factoryState`); neither may be moved onto the claim/validation hot path.

`tools/check_concurrency.py` enforces the structural rules; the same-deploy suite
`harness/concurrency_core.py` enforces the behaviour.

## Core invariants

- A claim is validated at most once; the Claim cell moves from `open` to
  `validated`/`rejected`/`withdrawn`/`expired` exactly once.
- The Claim cell creates exactly one K-Asset on validation; a public K-Asset factory is
  forbidden because it would allow a fake pair.
- K-Asset approval and rejection are transitions from `validated`/`conditional` only.
- Nesting is parent-owned; a duplicate child is refused under the parent's consume; an edge
  requires `(child.approvedAt, child.id) < (parent.approvedAt, parent.id)`.
- A value proposition is validated once; a K-Asset may reference only a validated VP.
- An Oracle case is decided once and executed once; the subject's private apply checks the
  case id and its own dispute state.
- A revoked credential cannot validate or approve a new event; past events remain.

## Citation headers

Every core deploy term starts with:

```rholang
// Why: ...
// Paper: @key p.N; @key2 p.N    (or "none (engineering infrastructure)")
// r-gen decision: ...
```

`tools/check_citations.py` verifies keys, page ranges, extract headings, and the papers'
SHA-256. Do not cite `@caase2018agenda`. Do not present a user decision as paper-derived;
the Pareto ledger labels every row.

## Testing

- `harness/unit_core.py` is the vertical slice.
- `harness/concurrency_core.py` is the same-deploy race suite.
- A suite that cannot reach a healthy devnet exits 2 (`not run`), never 0.
- `make spec-check parse-check docs-check` must pass before a commit. `make
  capabilities-check` is part of `spec-check`: every new `bundle+`, `Apply` handoff, proof
  channel or capability-bearing reply needs a row in `spec/audit/capabilities.yaml`.
- `make redteam-capabilities` runs RT-024..RT-037 on the local devnet; a new capability arm
  should add a probe or a register row and a HAZOP row.
- The Rust crates must pass `cargo fmt`, `clippy -D warnings`, and `cargo test`;
  `rgen-wasm` must pass `cargo check --target wasm32-unknown-unknown`.
- The web client must pass `npm --prefix web run typecheck`, `test`, `test:wasm` and
  `build`. Playwright runs against a seeded devnet, never against the testnet.
- The web client is not an indexer and may not invent entities, balances or statuses. A
  list is the local journal, a pasted share link or the seeded catalogue; every detail
  page re-reads the entity. Every write is a real signed deploy.
- Do not auto-retry a signed write in the browser. Record the deploy id, re-read the
  entity, and reconcile an unknown outcome with `deploy_status`.

## Papers and licensing

The papers are third-party copyrighted works, already public on Arweave and the authors'
websites, and included as cited reference material. They are not AGPL. Do not add
full-text extracts beyond the short page-cited quotations. Never describe NAIC/NSPE as
"Robles papers" without the institutional venue; see the manifest.

## Safety

- Never commit `.devnet/`, `.testnet/`, `.demo/` or private keys.
- Never deploy to a network with value. The Phase 1 audit is recorded but not independently
  reviewed; the core remains unaudited for deployment purposes.
- The public testnet is disposable and valueless, not production. It is opt-in: live
  commands require `--allow-live` (`TESTNET_ALLOW=--allow-live`). Use fresh keys under
  `.testnet/`; never reuse a devnet key. Do not retry a value-moving deploy blindly; use
  the op cache and reconcile the deploy id.
- Do not use `1/0` to clear a pending flag; use an explicit refusal/re-post path.
