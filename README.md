# r-gen — CoEngineers / Ingenesist contracts and proofs

**Devnet-only, no real value. Phase 1 audit recorded; Phase 2 in progress; independent review pending.**

r-gen is the first reasonably complete suite of Rholang contracts, paired with a Lean 4 model,
for the **CoEngineers and Ingenesist Project** vision set out in Dan Robles' papers:
engineering work becomes a claim, validation is its quality, the claim+validation pair is a
K-Asset, and qualifications, adjudication, and provenance stay with the asset.

The project is **r-gen**. The Lean namespace remains `RGen` because Lean identifiers cannot
contain a hyphen.

**Documentation:** <https://rhovision-org.github.io/r-gen/>

The suite expresses **claims**, **validations**, **value propositions**, **K-Assets**,
qualifications, adjudication, and asset-bound provenance. The "Pareto" test is the internal
design criterion for what stays in the core: remove a primitive and ask whether the remaining
set can still express the papers' claim → validation → approval handshake and the K-Asset. It
is not the public purpose of the repo. It deliberately does **not** tokenise, price, pay,
score risk, run panels, or administer a governance layer.

> The fundamental problem is that the value of engineering is invisible — there is little or
> no accounting of 'true' engineering value in society because there are few tools that
> accurately measure it. — Robles & Bowers, *Blockchain Engineering Stewardship* (2017)

> The claim serves as the quantity (definition) and the validation serves as the quality
> (characteristics). — Robles & Layton, *The Innovation Bank* (IMECE2020-23015, p.5)

> Each pairing forms a single node with two branches constituting a knowledge asset —
> 'K-asset' — which is memorialized by the creation of an electronic token awarded to each
> participant in a pair. — *The Innovation Bank*, p.4

The full quote-to-primitive map, including what was removed and why, is
`docs/src/reference/pareto-ledger.md`. Each primitive has a page under `docs/src/primitives/`
with paper quotes, code references, and Lean theorem names; the row-by-row linkage is
`docs/src/reference/paper-to-code.md`. The Pareto minimal set is `spec/pareto.yaml`,
checked by `tools/check_pareto.py`. The papers are indexed at `docs/papers/README.md`; the
code headers use citation keys and page numbers.

## Core (default install)

| Term | Primitive |
|---|---|
| `00_root.rho` | `GenRoot` — installer-gated client directory; not a runtime dependency |
| `10_identity.rho` | Per-address identity cell + first-writer-wins directory |
| `11_credentials.rho` | Genesis `Issuer` + per-credential cell + issued registry |
| `20_claim.rho` | Per-claim cell: work element, selection criteria, quantity/definition, clock, comments, value-proposition ref; creates the K-Asset on validation; private K-Asset library |
| `22_value.rho` | Per-value-proposition cell: propose, validate, comment, withdraw, dispute |
| `30_oracle.rho` | Per-case cell: one credential-proved adjudicator, evidence, decide, execute via the subject's private capability |
| `40_provenance.rho` | Per-asset cell: anchors, comments, verify |

Seven deploy terms, 16 catalogue components, 10 state cells, acyclic. There is no r-cash or
ERTP dependency.

## Extensions (deliberately not core)

KAT/receipt and pricing, r-cash payments, SPE/insurability risk, oracle panels, admin
governance, human-readable handles, Metcalfe/CAPM/WIKiD metrics, and the web client. The
core exposes approval/decision facts; an extension consumes them without the core calling
the extension. The Pareto ledger states the paper basis and removal reason for each.

## Race freedom and concurrency

Every entity is a **factory-created linear cell** with one writer. Mutating arms consume
first (`for (@s <- state)`), evaluate every guard on the post-consume state, and re-post
exactly once on every path. A second operation on the same entity blocks, observes the new
state, and refuses; two operations cannot both observe the same pre-state and both commit.

Independent entities do not share a mutable cell. The only serialization points are identity
creation and credential issuance; neither is on the claim/validation hot path. Oracle cases
receive the subject's private `applyDecision` capability in their closure, so a decision
cannot be applied to another K-Asset.

Proved: `RGen.core_races_not_representable` — in every `Run` of the versioned-cell model,
no two events on one cell share an expected generation; `RGen.core_arm_authority` — every
arm's decision factors through its consumed cell; the pair matrix in `spec/flows/races.yaml`
classifies 32 arm pairs (19 exclusive, 11 ordered, 2 independent). See
`docs/src/reference/race-freedom-proof.md`. The behavioural suite
(`harness/concurrency_core.py`) is regression evidence only, not the proof. The claim is
precise: **no shared mutable cell across independent entities; one writer per entity** —
not an absolute optimality theorem.

## Quickstart

Prerequisites: Docker, Python 3.12, an rholo checkout at `../RNodeRust`, and `mdbook`.

```sh
make venv
make build-check
make spec-check
make lean-check
make check-pareto
make check-docs-links
make parse-check
make docs-check

export RHOLO_DIR=../RNodeRust
DEVNET_PREFIX=rgen make devnet-up keys install
make unit-core
make unit-race
make unit-all
```

`make keys` generates the devnet's baked-in deployer plus fresh actor keys; no r-cash keys
file is needed. `DEVNET_PREFIX=rgen` starts an isolated `rgen-bootstrap` on 40403/40405 and
leaves any existing default devnet alone.

## Verification

On 2026-11-04, node `e2d073d`, the 7-term core installed on a fresh isolated devnet and the ten
behavioural suites passed. The record is `docs/src/reference/verification.md`. The pre-Pareto
12-term prototype is on tag `legacy-2026-11-04`; its 12/12 suite result is the baseline, not
the target.

`make lean-check` builds the Lean 4 model (`spec/lean/`), rejects unproved declarations,
checks the 192 theorems listed in `RGen/Audit.lean` (only `propext` and `Quot.sound`; no
`Classical.choice`), and checks the emitted conformance corpus. `make spec-check` includes
`check_audit`, which ties every deployed arm, HAZOP row, claim, and improvement to an
evidence-backed finding. The audit is in `spec/audit`, `spec/hazop`, `spec/proofs`, and
`spec/improvements`; its pages start at `docs/src/reference/audit-charter.md`. The
model and its honest limits are described in `docs/src/reference/formal-model.md` and
`docs/src/reference/concurrency-and-proofs.md`. The deployed contracts use the proof-URI
design; the race-freedom theorem is `core_races_not_representable` and the pair matrix is
`spec/flows/races.yaml`.

## Non-goals

- No token sale, pricing, transfer, or ERTP in the core.
- No payments, risk scoring, panels, admin, handles, or metrics in the core.
- No off-chain indexer: the chain is the backend; clients carry URIs/capabilities.
- No refinement claim: Lean proves the model, and the flow manifest plus corpus is
  traceability, not a refinement theorem. Arms not yet mapped are listed as `owed`.
- No claim that the papers use "Pareto" or define a ValueProposition state machine; the
  ledger labels those as the user's framing/decision.

## Repository map

```
contracts/src/deploy/       7 core terms
contracts/src/lib/          Auth, Time, List, Scope, KAsset
harness/                    installer, keys, per-primitive + behavioural suites
docs/papers/                seven PDFs, extracts, manifest, copyright notice
docs/src/                   mdBook: primitive pages, paper-to-code, Pareto ledger, formal model
docs/src/primitives/        one paper-cited page per primitive
spec/lean/                  Lean 4 model, Pareto proof set, race-freedom, audit, corpus emitter
spec/pareto.yaml            Pareto core manifest and docs/theorem boundary
spec/flows/, spec/vectors/  arm-to-theorem manifest, race matrix, emitted corpus
spec/audit/, spec/hazop/    findings, arm dispositions, HAZOP worksheet
spec/proofs/, spec/improvements/  claim/divergence ledger and ranked Rholang backlog
spec/                       legacy/extension vector material
tools/                      build, parse, measure, formal, boundary/concurrency/citation checks
crates/                     rgen-core, rgen-sdk, rgen-cli
legacy/                     the tagged pre-Pareto 12-term implementation
```

## License and papers

r-gen is AGPL-3.0-only. The papers are third-party copyrighted works, already public on
Arweave and the authors' websites, and are **not** covered by the AGPL; they are included as
cited reference material. See `docs/papers/README.md` and `THIRD_PARTY_NOTICES.md`.
