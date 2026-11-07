# Core arm reference

Replies are `(true, payload…)` or `(false, reason)`. Mutating arms consume the entity cell
first and re-post exactly once. Proofs are one-shot capabilities sent as
`bundle+{*Proof}` on a caller-supplied `proofCh`; the caller calls `Proof("take")` and checks
the payload. No proof URI is published.

Each section links the primitive page with the paper anchors and the Lean theorem names.

## Root and identity

- `GenRoot("resolve"|"get"|"keys"|"register", ...)` — installer-gated directory.
- `IdentityFactory("create", dId, profile, ret) -> (true, identityUri)`
- `IdentityDirectory("lookup"|"count", ...)`
- `Identity("get"|"update", ...)`

Paper: `@robles2016nspe p.40` (records/identity); `@zhong2019bridge p.4` (participants).
Lean: `Directory.create_unique`, `update_owner_requires_owner`.
See [Identity](../primitives/identity.md).

## Credentials

- `Issuer("get"|"authorize"|"covers", ...)` — immutable genesis issuer; no revoke arm.
  `authorize` takes a `dId` name and derives the caller with `authSubject`.
- `CredentialFactory("issue"|"verify"|"count", ...) -> (true, credentialUri)`
- `Credential("get"|"check"|"prove"|"revoke"|"renew"|"attest", ...)`
- `Proof("take", ret) -> (true, proofData)` once, then `(false, "used")`

Paper: `@mathews2017bim p.7`, `@zhong2019bridge p.6`, `@robles2016nspe p.25`,
`@robles2016naic p.9`. Lean: `C1_prove_requires_active`, `C2_revoke_blocks_prove`,
`C3_issuer_immutable`, `prove_snapshot`, `proof_take_once_versioned`.
See [Issuer, credential, proof](../primitives/credential.md).

## Claims and K-Assets

- `ClaimFactory("create"|"verify", ...)`
- `Claim("get"|"comments"|"comment"|"withdraw"|"expire"|"validate", ...)`
- K-Asset arms (created by the Claim): `get`, `approve`, `reject`, `proveApproved`, `nest`,
  `openDispute`, `children`, `revocation`, and the private `applyDecision`.

Paper: `@robles2020innovation p.4-5`, `@zhong2019bridge p.4-6`.
Lean: `ClaimState.validate_once`, `claim_validation_exactly_one_kasset`,
`K1_approve_credential`, `K2_approve_status`, `K3_nest_acyclic`.
See [Claim](../primitives/claim.md), [Validation](../primitives/validation.md),
[K-Asset](../primitives/k-asset.md).

## Value proposition

- `ValuePropositionFactory("propose"|"verify", ...)`
- `ValueProposition("get"|"comments"|"comment"|"withdraw"|"validate"|"proveValidated"|"openDispute"|"revocation", ...)`
- Private `applyDecision`.

Paper: `@mathews2017bim p.7,p.9` (paper-adjacent; no state machine defined).
Lean: `V1_validate_once`, `V2_dispute_blocks_prove`, `proveValidated_requires_validated`.
See [Value proposition](../primitives/value-proposition.md).

## Oracle

- `OracleFactory("open", subjectRef, caseReq, subjectApply, ret) -> (true, {id, uri})`
- `OracleCase("get"|"evidence"|"decide"|"execute"|"expire"|"close", ...)`

Paper: `@robles2016nspe p.25`, `@robles2016naic p.9`, `@mathews2017bim p.8`.
Lean: `O1_execute_bound_once`, `O2_close_finished`, `decide_once`, `execute_once`.
See [Oracle](../primitives/oracle.md).

## Provenance

- `ProvenanceFactory("create", assetRef, writers, ret) -> (true, {id, uri})`
- `Provenance("get"|"anchors"|"anchor"|"comment"|"verify", ...)`

Paper: `@robles2016nspe p.29`, `@zhong2019bridge p.3,p.6`.
Lean: `P1_anchors_append_only`, `anchor_unique`, `verify_monotone`.
See [Provenance](../primitives/provenance.md).

## Creation registries

`CredentialFactory`, `ClaimFactory`, `ValuePropositionFactory`, and `IdentityFactory` write
append-only creation registries. See [Creation registries](../primitives/registry.md).
