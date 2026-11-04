# Claim

## Paper anchors

> "The claim serves as the quantity (definition) and the validation serves as the quality
> (characteristics)." — `@robles2020innovation p.5`

> "'Claim' and 'Validation' represent a key mechanism i.e. the 'handshake'." — `@zhong2019bridge p.4`

> "pre-defined and agreed upon 'clock' … and all participants can see the specific actions
> to be taken and their status" — `@zhong2019bridge p.5`

## What the paper means

A claim states the work element, its quantity, its definition, and the agreed clock. It is the
quantity half of the handshake; validation is the quality half. The claim is a durable record,
not a transient message.

## How the Rholang expresses it

- `contracts/src/deploy/20_claim.rho` — `ClaimFactory@"create"` checks the required fields
  and appends the claim URI to `claimRegistryState`.
- The `Claim` cell stores `work`, `selectionCriteria`, `statementHash`, `definitionHash`,
  `quantity`, `evidence`, `valuePropositionRef`, `deadlineHeight`, `commentUntilHeight`, and
  `comments`.
- `Claim@"comment"` appends inside the comment window; `Claim@"withdraw"` and `@"expire"` are
  terminal; `Claim@"validate"` consumes the cell and creates the K-Asset.

## What the Lean proves

- `RGen.ClaimState.validate_once` — a claim validates once.
- `RGen.ClaimState.validate_requires_open`,
  `validate_requires_non_claimant`, `validate_within_deadline`,
  `validate_requires_subject`, `validate_requires_no_kasset`.
- `RGen.ClaimState.validate_creates_exactly_one_kasset` — a validated claim has exactly one
  K-Asset reference.
- `RGen.claim_validate_blocks_comment`, `claim_validate_expire_two_way`,
  `claim_validate_withdraw_two_way`, `claim_comment_comment_appends`.

## Deliberately excluded

Global claim registries for search, human-readable identifiers, and cross-claim aggregation
are extensions. The core registry is append-only creation only.

## See also

- [Validation](validation.md)
- [K-Asset](k-asset.md)
- [Paper-to-code matrix](../reference/paper-to-code.md)
- Suites: `harness/unit_claim.py`, `harness/unit_core.py`
