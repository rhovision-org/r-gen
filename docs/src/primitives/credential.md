# Issuer, credential, and proof

## Paper anchors

> "A 'Permissioned by Qualifications Blockchain', facilitated by an Oracle…" — `@mathews2017bim p.7`

> "permissioned by qualifications" and the validator must be qualified — `@zhong2019bridge p.6`

> "the adjudicator is deemed the most appropriate person" — `@robles2016nspe p.25`

> "An Oracle contract is an adjudicated contract…" — `@robles2016naic p.9`

## What the paper means

The papers put qualification before action: a validator, approver, or adjudicator must hold a
credential that a recognized issuer covers. The core therefore makes the credential a linear
cell and the proof a one-shot capability, not a caller-supplied boolean.

## How the Rholang expresses it

- `contracts/src/deploy/11_credentials.rho` — the genesis `Issuer` is immutable and has no
  revoke arm. `Issuer@"authorize"` and `"covers"` are monotone reads of `issuerState`.
- `CredentialFactory@"issue"` rejects self-issue and appends the credential to
  `factoryState`; `CredentialFactory@"verify"` reads that append-only registry.
- `Credential@"prove"` consumes `credState`, checks subject/active/scope/issuer, creates a
  one-shot `Proof` cell, re-posts the credential, and returns the proof URI.
- `Credential@"revoke"`, `"renew"`, and `"attest"` consume the same cell.

## What the Lean proves

- `RGen.C1_prove_requires_active` — a proof requires an active credential at the stated height.
- `RGen.C2_revoke_blocks_prove` — a revoked credential cannot prove.
- `RGen.C3_issuer_immutable` — the issuer transition relation has no constructor.
- `RGen.CredentialState.prove_snapshot` — the proof payload is a pre-revoke snapshot.
- `RGen.core_arm_authority` and `RGen.proof_take_once_versioned` — the decision is authority
  from the consumed credential plus the one-shot proof payload.
- Pair matrix: `credential_prove_revoke_never_after`,
  `credential_prove_revoke_snapshot`, `credential_attest_same_never_after`.

## Deliberately excluded

Issuer rotation/revocation is a governance extension. Reputation and issuer chains are
extensions. The core issuer is one genesis cell.

## See also

- [Paper-to-code matrix](../reference/paper-to-code.md)
- [Pareto ledger](../reference/pareto-ledger.md)
- [Race-freedom proof](../reference/race-freedom-proof.md)
- Suites: `harness/unit_credentials.py`, `harness/integration_core.py`
