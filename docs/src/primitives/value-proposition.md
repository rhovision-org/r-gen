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

## What the Lean proves

- `RGen.V1_validate_once` — validation is once.
- `RGen.V2_dispute_blocks_prove` — a disputed proposition cannot prove validated.
- `RGen.VPState.validate_requires_non_proposer`, `proveValidated_requires_validated`,
  `openDispute_requires_status`, `terminal_no_transition`.
- Pair matrix: `vp_validate_withdraw_two_way`,
  `vp_proveValidated_openDispute_ordered`, `vp_decision_decision_never_after`.

## Deliberately excluded

The papers do not define the state machine, so the states and guards are a user decision. The
core does not price, reward, mint, or score the proposition; those are extensions.

## See also

- [K-Asset](k-asset.md)
- [Pareto ledger](../reference/pareto-ledger.md) (marks this as a user decision)
- Suite: `harness/unit_value.py`
