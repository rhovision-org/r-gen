# Core arm reference

Replies are `(true, payload…)` or `(false, reason)`. Capabilities are passed as quoted names;
a credential, K-Asset or case capability is always checked by the callee.

## Root and identity

- `GenRoot("resolve"|"get"|"keys"|"register", ...)` — installer-gated directory.
- `IdentityFactory("create", dId, profile, ret) -> (true, identityUri)`
- `IdentityDirectory("lookup"|"count", ...)`
- `Identity("get"|"update", ...)`

## Credentials

- `Issuer("get"|"authorize"|"covers"|"revoke", ...)`
- `CredentialFactory("issue"|"verify"|"count", ...) -> (true, credentialUri)`
- `Credential("get"|"check"|"revoke"|"renew"|"attest", ...)`

## Claims and K-Assets

- `ClaimFactory("create", dId, claimReq, ret) -> (true, {id, uri})`
- `Claim("get"|"comments"|"comment"|"withdraw"|"expire"|"validate", ...)`
- K-Asset arms (created by the Claim): `get`, `approve`, `reject`, `nest`, `openDispute`,
  `children`, `revocation`, and the private `applyDecision`.

## Value proposition

- `ValuePropositionFactory("propose", dId, req, ret) -> (true, {id, uri})`
- `ValueProposition("get"|"comments"|"comment"|"withdraw"|"validate"|"openDispute"|"revocation", ...)`
- Private `applyDecision`.

## Oracle

- `OracleFactory("open", subjectRef, caseReq, subjectApply, ret) -> (true, {id, uri})`
- `OracleCase("get"|"evidence"|"decide"|"execute"|"expire"|"close", ...)`

## Provenance

- `ProvenanceFactory("create", assetRef, writers, ret) -> (true, {id, uri})`
- `Provenance("get"|"anchors"|"anchor"|"comment"|"verify", ...)`
