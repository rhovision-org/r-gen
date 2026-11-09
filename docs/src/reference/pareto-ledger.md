# Pareto ledger

The Pareto test: remove a primitive and ask whether the remaining set can still express the
papers' **claim → validation → approval** handshake, the **K-Asset**, and a **value
proposition**. If it can, the removed thing was not core.

Labels: **paper-derived** (a passage requires it), **paper-adjacent** (a passage names the
idea but does not define its mechanism), **user decision** (the user asked for it), or
**engineering infrastructure** (needed to run, not a value primitive).

## Core (default install and verification)

| Primitive | Paper claim | Necessity argument | Status |
|---|---|---|---|
| Identity | Papers assume identified practitioners; no direct definition | A claim and a validation need authenticated parties | Paper-adjacent / user decision |
| Issuer & Credential | "Permissioned by Qualifications" `@mathews2017bim p.7`; "validation of credentials should be in place before validation of events" `@zhong2019bridge p.6` | Without a qualification gate, any key can validate any claim; the handshake loses its meaning | Paper-derived |
| Claim | "The claim serves as the quantity (definition)" `@robles2020innovation p.5`; Work Element / Selection Criteria `@zhong2019bridge p.4` Fig.1 | Without a quantity/definition record there is nothing to validate | Paper-derived |
| Validation | "the validation serves as the quality (characteristics)" `@robles2020innovation p.5` | Without quality there is no K-Asset, only an assertion | Paper-derived |
| Approval | "'Approval' represents an acceptable completion" `@zhong2019bridge p.4` | The third step of the handshake; it is where the K-Asset becomes acceptable and where liability can move | Paper-derived |
| K-Asset | "Each pairing forms a single node with two branches constituting a knowledge asset – 'K-asset'" `@robles2020innovation p.4` | The fundamental unit; it is the durable claim+validation pair | Paper-derived |
| ValueProposition | "This is in essence 'the new value proposition'" `@mathews2017bim p.7`; "develop a 'new value proposition' to extract reward … intrinsic intangible value" p.9 | The user's explicit primitive. The papers name the idea but define no state machine; the separate cell is a user decision. It now carries Dan's quantity/quality/variance description; the schema is [quantity, quality and variance](variance-model.md), and the numeric variance rate is a user specification, not a paper result | Paper-adjacent / user decision |
| Oracle | "the adjudicator … is deemed the most appropriate person" `@robles2016nspe p.25`, `@robles2016naic p.9`, `@mathews2017bim p.8` | A validation can be disputed; adjudication is the paper's mechanism for resolving it and assigning liability | Paper-derived |
| Provenance | "The asset becomes the keeper of its own information" `@robles2016nspe p.29`; sealing/provenance `@zhong2019bridge p.3,p.6` | The K-Asset's record must stay with the asset, not in a detached global book | Paper-derived |
| Clock & comments | "pre-defined and agreed upon 'clock'" and "Stakeholder comment period" `@zhong2019bridge p.5` | The handshake's timing and comment rights are part of the paper's process | Paper-derived |
| Liability transfer | "assign, limit, or transfer liability" `@robles2016nspe p.25`; "Tokens issuance marks points where risk is transferred" `@zhong2019bridge p.6` | Approval and oracle decisions must record who bears the risk | Paper-derived |
| GenRoot | No paper passage | Install-time discovery only; core contracts are wired at install and never resolve it at runtime | Engineering infrastructure |

Each core primitive has a page with paper quotes, the Rholang arm/field references, and the
Lean theorem names under `docs/src/primitives/`; the row-by-row linkage is
[paper-to-code](paper-to-code.md).

## Extensions (excluded from the default build)

| Extension | Paper basis | Why not core |
|---|---|---|
| KAT / receipt / pricing | "receipt token(s) issued to each participant" `@robles2020innovation p.4`; "Tokens issuance marks points where risk is transferred" `@zhong2019bridge p.6`; Quant/#AECoin `@robles2017stewardship p.3`, `@mathews2017bim p.7,p.9` | Tokenisation/pricing is explicitly not the primary objective. The core mints nothing; a receipt extension must choose validation (IMECE) or approval (Bridge) timing. |
| Risk / SPE / insurability | Risk = S×P×E `@robles2020innovation p.3`; three insurability questions `@robles2016naic p.4`, `@robles2016nspe p.14` | A key application, but not needed to express a claim/validation/K-Asset. It also merges two different frameworks (S×P×E exposure vs insurability consequence); keep the distinction in the extension. |
| Payments / r-cash | "Payment can be promptly initiated" `@zhong2019bridge p.4`; oracle payment `@robles2016nspe p.25` | Settlement is an application of the core; the core only records approval/decision facts. |
| Oracle panels / votes | The papers say one "most appropriate person", not a weighted panel | Panels are an extension; the core has a single adjudicator. |
| Admin / governance | No paper basis | Multisig, pause, freeze and params are operational. The core Root is installer-only. |
| Handles | No paper basis | The REV address is identity; human-readable names are an extension. |
| Metrics / WIKiD / Metcalfe / CAPM | WIKiD `@robles2020innovation p.6-7`; network value `p.5` | Metrics, not primitives. |
| Curiosumé | `@robles2016nspe p.25` | A named mechanism for decentralizing the oracle pool; an extension. |

## What was removed or narrowed

- **Four-axis quality rubric** (completeness/correctness/traceability/fitness): no paper
  defines these dimensions. The core carries an opaque `quality` map and a `qualityNotesHash`;
  the validator supplies the characteristics.
- **Fixed reputation tiers and 50/50 split**: the papers say "in proportion to reputation",
  not these numbers. Reputation is an extension.
- **Risk class ladder and validator/approver levels**: an extension policy, not core.
- **Weighted oracle panels / tally**: the core has one adjudicator; panels are an extension.
- **ERTP KAT, transfer, slashing**: the core does not mint or transfer; a receipt extension
  owns those races.
- **Admin multisig / pause / freeze / setParams**: the core has no admin arms.
- **Handles**: the identity directory is keyed by REV address.
- **WorkBook / global books**: the core uses per-claim cells and the claim carries work
  metadata.
- **Dead `configs/rgen.json` and `GenAdmin.params`**: removed; core constants live where
  they are used.

## Paper facts the docs must not overclaim

- "Pareto" does **not** appear in the seven papers. "Primitive" appears once, rhetorically.
  The Pareto framing is the user's.
- "Value proposition" is a phrase in BIM, not a defined state machine. The separate
  ValueProposition cell is a user decision.
- IMECE mints at validation; Bridge supports risk-transfer at approval. The core avoids the
  choice by not minting.
