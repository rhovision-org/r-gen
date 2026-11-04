# RGen — Pareto core

**Devnet-only, unaudited, no real value.**

RGen is the Pareto-efficient core of the engineering-technology primitives suggested by the
Dan Robles papers: it expresses **claims**, **validations**, **value propositions**,
**K-Assets**, qualifications, adjudication, and asset-bound provenance. It deliberately does
**not** tokenise, price, pay, score risk, run panels, or administer a governance layer.

> The fundamental problem is that the value of engineering is invisible — there is little or
> no accounting of 'true' engineering value in society because there are few tools that
> accurately measure it. — Robles & Bowers, *Blockchain Engineering Stewardship* (2017)

> The claim serves as the quantity (definition) and the validation serves as the quality
> (characteristics). — Robles & Layton, *The Innovation Bank* (IMECE2020-23015, p.5)

> Each pairing forms a single node with two branches constituting a knowledge asset —
> 'K-asset' — which is memorialized by the creation of an electronic token awarded to each
> participant in a pair. — *The Innovation Bank*, p.4

The full quote-to-primitive map, including what was removed and why, is
`docs/src/reference/pareto-ledger.md`. The papers are indexed at `docs/papers/README.md`;
the code headers use citation keys and page numbers.

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

Measured: `harness/concurrency_core.py` passes one-of-two validation, one-of-two approval,
exactly-one oracle apply, cross-subject isolation, two comments both stored, eight independent
claims validating in one deploy, and revoked-credential refusal. The claim is precise: **no
shared mutable cell across independent entities; one writer per entity** — not an absolute
optimality theorem. See `docs/src/reference/design-rationale.md`.

## Quickstart

Prerequisites: Docker, Python 3.12, an rholo checkout at `../RNodeRust`, and `mdbook`.

```sh
make venv
make build-check
make spec-check
make parse-check
make docs-check

export RHOLO_DIR=/home/patrick/RNodeRust
DEVNET_PREFIX=rgen make devnet-up keys install
make unit-core
make unit-race
make unit-all
```

`make keys` generates the devnet's baked-in deployer plus fresh actor keys; no r-cash keys
file is needed. `DEVNET_PREFIX=rgen` starts an isolated `rgen-bootstrap` on 40403/40405 and
leaves any existing default devnet alone.

## Verification

On 2026-11-04, node `e2d073d`, the 7-term core installed on a fresh isolated devnet and both
core suites passed. The record is `docs/src/reference/verification.md`. The pre-Pareto
12-term prototype is on tag `legacy-2026-11-04`; its 12/12 suite result is the baseline, not
the target.

## Non-goals

- No token sale, pricing, transfer, or ERTP in the core.
- No payments, risk scoring, panels, admin, handles, or metrics in the core.
- No off-chain indexer: the chain is the backend; clients carry URIs/capabilities.
- No Lean/flow claim of refinement; the formal artefacts are owed.
- No claim that the papers use "Pareto" or define a ValueProposition state machine; the
  ledger labels those as the user's framing/decision.

## Repository map

```
contracts/src/deploy/       7 core terms
contracts/src/lib/          Auth, Time, List, Scope, KAsset
harness/                    installer, keys, core + race suites
docs/papers/                six cited PDFs, extracts, manifest, licence notice
docs/src/                   mdBook: Pareto ledger, design rationale, adversarial review
spec/                       legacy/extension flow and vector material
tools/                      build, parse, measure, boundary/concurrency/citation checks
crates/                     rgen-core, rgen-sdk, rgen-cli
legacy/                     the tagged pre-Pareto 12-term implementation
```

## License and papers

RGen is AGPL-3.0-only. The papers are third-party copyrighted works, **not** covered by the
AGPL; see `docs/papers/README.md` and `THIRD_PARTY_NOTICES.md`. For a public release,
replace non-redistributable PDFs with links and keep the short page-cited extracts.
