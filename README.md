# RGen

**Qualification-gated knowledge-asset primitives for the rholo network.**

> **Status: devnet-only, unaudited, no real value.** Do not deploy this to a network that
> matters. On 2026-11-04 the twelve implemented behavioural suites passed on a fresh rholo
> devnet (node `e2d073d`, core rail). The r-cash escrow and dispute suites are **owed**;
> treat every claim below as a claim to verify, not an assurance.

RGen makes engineering value measurable at the point where risk moves: a qualified
claimant asserts a quantity, a qualified validator asserts its quality, and the chain
issues a transferable receipt and an immutable record; a qualified adjudicator can then
approve the next step or release payment through r-cash.

It is a small set of smart-contract primitives inspired by the engineering-technology
papers of Dan Robles. It is **not** a complete marketplace, insurer, or governance system.

## Why this exists

The papers argue that engineering value is real but invisible because nothing measures
both its **quantity** and its **quality**. The executable core is the K-Asset: a claim
paired with a validation, memorialized by a token awarded to both participants.

> "The fundamental problem is that the value of engineering is invisible – there is little
> or no accounting of 'true' engineering value in society because there are few tools that
> accurately measure it." — Robles & Bowers, *Blockchain Engineering Stewardship* (2017)

> "Each pairing forms a single node with two branches constituting a knowledge asset –
> 'K-asset' – which is memorialized by the creation of an electronic token awarded to each
> participant in a pair." — Robles et al., *The Innovation Bank*, IMECE2020-23015

> "'Claim' and 'Validation' represent a key mechanism i.e. the 'handshake'." —
> *Blockchain and Bridge Construction*

> "The validity of the Oracle is what establishes tangibility and invokes law—therefore,
> money and property." — NSPE, *Blockchain Technology* whitepaper (2016)

> "The asset becomes the keeper of its own information." — NSPE whitepaper, quoting Bruce
> Cahan

The full quote-to-primitive map is in `docs/src/reference/paper-map.md`.

## What is in here

| Family | Primitive | What it does |
|---|---|---|
| Identity & qualification | `IdentityBook`, `CredentialBook` | One profile per REV address; issuer-scoped credentials with discipline, jurisdiction, role, level, expiry and revocation. Validators and oracles must themselves be qualified. |
| Knowledge assets | `WorkBook`, `KAssetBook`, `ProvenanceBook` | Work elements, claims, one validation per claim, approval, nesting, seals and immutable document anchors. |
| Adjudication & risk | `RiskBook`, `OracleBook`, `PaymentBook` | SPE risk (`S×P×E`), the three-question insurability test, qualification-gated oracle panels, liability and r-cash payment instructions. |
| Receipt | `TokenBook` | A transferable ERTP token (**KAT**) minted once per approved K-Asset to the claimant and validator. Reputation is net lifetime **earned** KAT and never moves on transfer. |

KAT is a receipt, not a security: no governance rights, no dividends, no sale, no
issuance schedule.

## Architecture

```
rholo (RNodeRust)          consensus, native ERTP, REV, registry
  └── r-cash (pinned)      accounts, asset resolver, clock, settlement rail
        └── RGen           identity, credentials, K-Assets, risk, oracle, KAT
```

The twelve RGen terms install after r-cash. Every domain contract resolves its peers and
the admin guard through `GenRoot`; it stores the r-cash Root URI in the payments adapter
and resolves r-cash capabilities per call.

## Quickstart

Prerequisites: Docker, Python 3.12, an rholo checkout at `../RNodeRust`, an r-cash
checkout at `../Rholphin`, and `mdbook` for the docs.

```sh
make venv
make build-check
make spec-check
make parse-check          # uses ../RNodeRust by default

# fresh devnet on 40403/40405/40402; leaves other networks alone
make devnet-up
make rcash-keys
make rcash-bootstrap
make keys
make install
make unit-journey
make unit-all
```

If a default devnet volume already exists, bring up an isolated network instead:

```sh
DEVNET_PREFIX=rgen make devnet-up keys install unit-all
```

The isolated prefix is for the core rail. Installing r-cash still expects the default
`devnet-bootstrap` container.

If you already have a devnet and an r-cash manifest, skip `devnet-up` and point
`RGEN_NODE` at it.

## Contract map

| # | Term | Contracts | Registers |
|---|---|---|---|
| 00 | `00_root.rho` | `GenRoot` | `component:root` |
| 01 | `01_kernel.rho` | `Clock`, `Verifier`, `Codec` | `component:clock`, `component:verifier`, `component:codec` |
| 02 | `02_admin.rho` | `AdminGuard`, `GenAdmin` | `component:admin-guard`, `component:admin` |
| 10 | `10_identity.rho` | `IdentityBook` | `component:identity` |
| 11 | `11_credentials.rho` | `CredentialBook` | `component:credential-book` |
| 12 | `12_token.rho` | `TokenBook` | `component:token` |
| 20 | `20_work.rho` | `WorkBook` | `component:work-book` |
| 21 | `21_kasset.rho` | `KAssetBook` | `component:kasset-book` |
| 22 | `22_provenance.rho` | `ProvenanceBook` | `component:provenance-book` |
| 30 | `30_risk.rho` | `RiskBook` | `component:risk-book` |
| 40 | `40_payments.rho` | `PaymentBook` | `component:payments` |
| 50 | `50_oracle.rho` | `OracleBook` | `component:oracle` |

Hashes are lowercase hex strings. Amounts are integers in 8-decimal base units. The KAT
unit mint is 100 KAT; a full-quality approval mints 50 KAT to the claimant and 50–75 KAT
to the validator, weighted by net lifetime earned KAT.

## Refusal semantics

Every arm replies `(true, payload…)` or `(false, reason)`. A refusal after value has moved
fails the deploy with `1/0` so the block rolls back. A permissionless crank (mint, execute,
oracle hooks) reads canonical state; it cannot choose an outcome, payee or amount.

## Non-goals

- Metcalfe/CAPM valuation metrics are deferred.
- The web client is deferred.
- No token sale, governance, dividends, or insurance contract.
- No off-chain indexer or database: the chain is the backend.
- No claim that the Lean/flow artefacts refine the deployed Rholang; they are models.

## Repository map

```
contracts/src/{lib,deploy}/   sources; deploy terms 00..50
contracts/build/deploy/       committed rendered terms
contracts/components.json     component/state-cell/dependency catalogue
crates/rgen-core/             pure domain: ids, math, models, terms
crates/rgen-sdk/              typed client over the pinned r-cash crates
crates/rgen-cli/              `rgen-cli`
harness/                      Python behavioural suites and installer
configs/                      devnet, r-cash and RGen parameters
docs/src/                     mdBook
spec/                         flows, vectors, invariants, acceptance
tools/                        build, measure, parse, check scripts
```

## Provenance

The seven source papers are in this directory. The repository is AGPL-3.0-only; see
`LICENSE` and `THIRD_PARTY_NOTICES.md`. The node and r-cash dependencies are AGPL; their
pinned revisions are recorded in `Cargo.toml`, `configs/rholo.json`, and
`configs/rcash.json`.
