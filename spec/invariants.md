# RGen invariants (normative)

## Qualification

- **Q1.** A validation succeeds only if the validator holds an active credential matching
  the claim's discipline and jurisdiction, with role `validator`, at the event height.
- **Q2.** Revocation is monotone and non-retroactive: past validations remain; future
  gates fail. Revoking an issuer lazily invalidates every credential it issued.
- **Q3.** A subject cannot issue a credential to itself.

## Knowledge assets

- **K1.** At most one validation per claim.
- **K2.** Validator ≠ claimant; approver ≠ claimant and ≠ validator.
- **K3.** Approval requires a `validated` or `conditional` K-Asset.
- **K4.** KAT is minted exactly once per K-Asset, only after approval. Nesting never mints.
- **K5.** A revoked K-Asset cannot be approved, nested, or minted.
- **K6.** Nesting forms a forest: no cycles, no duplicate child, same discipline and
  jurisdiction.

## Token

- **T1.** `totalSupply` changes only on mint; transfers preserve it.
- **T2.** `earned` changes only on mint and adjudicated slashing; transfers never change it.
- **T3.** The escrow purse is an empty issuer purse; no arm exposes mint authority.

## Risk

- **R1.** Each factor is at least 1; `score = S × P × E` in 1..100.
- **R2.** `insurable` iff the exposure, probability, consequence basis and consequence
  reference are non-empty and the factors are in range.
- **R3.** An uninsurable assessment cannot be attested, linked, or approved against.

## Oracle and payment

- **O1.** One vote per panelist; only seated panelists vote.
- **O2.** A decision is recorded only by the sole seated adjudicator or by weighted
  threshold; no admin arm writes a decision.
- **O3.** Payment executes only against a canonical decision.
- **O4.** Execution is idempotent: each step checks its flag, and a hold pays once.
- **O5.** Permissionless cranks read canonical state and cannot choose outcome, payee or
  amount.
