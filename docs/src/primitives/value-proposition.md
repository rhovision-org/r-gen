# Value proposition

## Paper anchors

> "This is in essence 'the new value proposition'." — `@mathews2017bim p.7`

> "develop a 'new value proposition' to extract reward … also the intrinsic intangible
> value" — `@mathews2017bim p.9`

## What the paper means

The papers name a "new value proposition" and connect it to intrinsic intangible value and
reward. They do **not** define a value-proposition state machine. r-gen makes it a separate,
user-requested primitive: a proposition cell that a qualified validator can validate, that can
be disputed, and whose validated state can be proved to an approver.

## How the Rholang expresses it

- `contracts/src/deploy/22_value.rho` — `ValuePropositionFactory@"propose"` creates a
  per-proposition cell and appends it to `vpRegistryState`.
- `ValueProposition@"validate"` consumes the cell, resolves the credential by URI, calls
  `Credential@"prove"`, takes/checks the proof, and commits the validation.
- `ValueProposition@"proveValidated"` creates a one-shot validated proof for an approver.
- `ValueProposition@"withdraw"` is proposed-only; `@"openDispute"` accepts proposed/validated
  and refuses a second dispute; `Apply@"applyDecision"` resolves upheld/revoked/partial.

## Quantity, quality and variance

A proposal now requires the asset description: `quantity = {unit, mean}`,
`quality = {kind, spec, scale, mean}`, and
`variance = {quantityBps, qualityBps, n}`. The variance rates are the dimensionless second
moments `σ² / mean²` in basis points; the quality mean uses the K-Asset's 4..20 rubric.
The full schema and its paper basis are in [quantity, quality and variance](../reference/variance-model.md).
The fields are descriptive; r-sure consumes them as its risk input.

## What the Lean proves

- `RGen.V1_validate_once` — validation is once.
- `RGen.V2_dispute_blocks_prove` — a disputed proposition cannot prove validated.
- `RGen.VPState.validate_requires_non_proposer`, `proveValidated_requires_validated`,
  `openDispute_requires_status`, `terminal_no_transition`.
- Pair matrix: `vp_validate_withdraw_two_way`,
  `vp_proveValidated_openDispute_ordered`, `vp_decision_decision_never_after`.

## Deliberately excluded

The papers do not define the state machine, so the states and guards are a user decision. The
core does not price, reward, mint, or score the proposition; those are extensions. The
quantity/quality/variance fields are Dan's specification, not a paper-derived schema, and the
variance is descriptive until r-sure interprets it.

## See also

- [K-Asset](k-asset.md)
- [Pareto ledger](../reference/pareto-ledger.md) (marks this as a user decision)
- Suite: `harness/unit_value.py`
