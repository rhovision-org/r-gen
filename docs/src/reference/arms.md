# Arm reference

Replies are `(true, payload…)` or `(false, reason)`. Hashes are lowercase hex strings.
Amounts are integers in base units.

## Identity

- `IdentityBook("register", dId, profile, ret) -> (true, subject)`
- `IdentityBook("update", dId, patch, ret)`
- `IdentityBook("profile"|"byHandle"|"count", ...)`
- `IdentityBook("admin", nonce, action, args, sigs, ret)`

## Credentials

- `CredentialBook("issue", dId, req, ret) -> (true, credId)`
- `CredentialBook("renew", dId, credId, expiresAt, evidenceHash, ret)`
- `CredentialBook("revoke", dId, credId, reason, ret)`
- `CredentialBook("attest", dId, credId, hash, ret)`
- `CredentialBook("valid", subject, requirement, atHeight, ret) -> (true, bool, credId|reason)`
- `CredentialBook("pool", requirement, ret) -> (true, [subject])`
- `CredentialBook("creds"|"credential"|"issuer"|"issuers", ...)`

## Work and K-Assets

- `WorkBook("openWork", dId, work, ret) -> (true, workId)`
- `WorkBook("claim", dId, workId, claim, ret) -> (true, claimId)`
- `WorkBook("amend"|"withdraw", dId, claimId, ..., ret)`
- `WorkBook("close", claimId, status, kassetId, ret)`
- `KAssetBook("validate", dId, claimId, validation, ret) -> (true, validationId, kassetId)`
- `KAssetBook("approve", dId, kassetId, approval, ret) -> (true, approvalId)`
- `KAssetBook("reject", dId, kassetId, reason, ret)`
- `KAssetBook("nest", dId, parentId, childIds, ret)`
- `KAssetBook("mintAuthorization", kassetId, ret)`
- `KAssetBook("oracleApprove"|"markDisputed"|"revoke", caseId, kassetId, ret)`
- `KAssetBook("kasset"|"validation"|"approval"|"kassetsOf"|"validationsOf"|"revocation", ...)`

## Token

- `TokenBook("brand"|"supply"|"balance"|"reputation"|"history", ...)`
- `TokenBook("transfer", dId, to, amount, memo, ret)`
- `TokenBook("deposit"|"withdraw", dId, ..., ret)`
- `TokenBook("newPurse", ret)`
- `TokenBook("mintForKAsset", kassetId, ret)`
- `TokenBook("revokeEarned", kassetId, ret)`

## Provenance

- `ProvenanceBook("seal", dId, seal, ret) -> (true, sealId)`
- `ProvenanceBook("anchor", dId, ref, doc, ret) -> (true, anchorId)`
- `ProvenanceBook("comment", dId, ref, comment, ret) -> (true, commentId)`
- `ProvenanceBook("verify", ref, hash, ret) -> (true, bool)`

## Risk

- `RiskBook("assess", dId, assessment, ret) -> (true, riskId, insurable)`
- `RiskBook("attest", dId, riskId, hash, ret)`
- `RiskBook("link", dId, riskId, kassetId, ret)`
- `RiskBook("gate", riskId, ret) -> (true, {insurable, score, class, ...})`

## Oracle

- `OracleBook("open", dId, caseReq, ret) -> (true, caseId)`
- `OracleBook("evidence", dId, caseId, evidence, ret)`
- `OracleBook("empanel"|"empanelWith", ..., ret)`
- `OracleBook("vote", dId, caseId, vote, ret)`
- `OracleBook("tally"|"decide"|"execute"|"close", ..., ret)`
- `OracleBook("paymentInstruction", caseId, ret)`
- `OracleBook("case"|"casesOf"|"panelOf"|"decisionOf", ...)`

## Payments

- `PaymentBook("health"|"platformOwner"|"ensureAccount"|"accountOf", ...)`
- `PaymentBook("fund", dId, intent, payment, ret) -> (true, holdId)`
- `PaymentBook("executeCase", caseId, ret)`
- `PaymentBook("hold"|"holds", ...)`
- `PaymentBook("admin", nonce, action, args, sigs, ret)`

## Admin payload

`rgen:admin:v1|<domain>|<nonce>|<action>|<arg0>,<arg1>,...`, hashed with blake2b256 and
signed with DER secp256k1. Admin arguments are flat strings and integers.
