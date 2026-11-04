# Validation

## Paper anchors

> "The claim serves as the quantity (definition) and the validation serves as the quality
> (characteristics)." — `@robles2020innovation p.5`

> "'Claim' and 'Validation' represent a key mechanism i.e. the 'handshake'." — `@zhong2019bridge p.4`

> "validation of credentials should be in place before validation of events" — `@zhong2019bridge p.6`

## What the paper means

Validation is the quality half of the handshake. It requires a qualified validator who is not
the claimant, a credential proof, a verdict, and evidence/quality records. It is the moment the
claim and validation pair becomes a K-Asset.

## How the Rholang expresses it

- `Claim@"validate"` consumes `claimState`, rejects self-validation and late validation,
  verifies the credential URI in `ClaimFactory`/`CredentialFactory`, resolves the credential,
  calls `Credential@"prove"`, takes and checks the proof (subject, credential URI, height),
  then calls `finalizeValidation`.
- `finalizeValidation` maps the verdict to the claim status and K-Asset status, calls
  `makeKAsset`, and commits the claim with `validationRef` and `kassetRef`.

## What the Lean proves

- `RGen.ClaimState.validate_once` and `validate_requires_non_claimant`.
- `RGen.ClaimState.validate_within_deadline` and `validate_expired_after_deadline`.
- `RGen.ClaimState.validate_requires_subject` and `validate_sets_kasset`.
- `RGen.C1_prove_requires_active` / `C2_revoke_blocks_prove` — the credential proof is the
  authority, not a peek.
- `RGen.claim_validation_exactly_one_kasset` — composition with the K-Asset.

## Deliberately excluded

Validator panels, weighted votes, reputation weighting, and off-chain quality scoring are
extensions. The core records the verdict and quality hashes.

## See also

- [Claim](claim.md)
- [K-Asset](k-asset.md)
- [Race-freedom proof](../reference/race-freedom-proof.md)
- Suite: `harness/unit_claim.py`
