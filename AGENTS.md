# RGen engineering rules

This file is binding for humans and agents working in this repository. If a rule here
conflicts with convenience, the rule wins.

## Authority order

1. The deployed Rholang in `contracts/src/deploy/` is the implementation.
2. `spec/` is normative where it disagrees with `docs/`.
3. `docs/` explains; it does not overrule source.
4. The pinned rholo and r-cash revisions are fixed. Do not float them.

## Non-negotiable invariants

- One validation per claim; validator ≠ claimant.
- Approver ≠ claimant and ≠ validator.
- A K-Asset is approved only after a `validated` or `conditional` validation.
- KAT is minted exactly once per K-Asset, only after approval. Nesting never mints.
- A revoked K-Asset cannot be approved, nested, or minted.
- `earned` is net lifetime earned KAT; transfers never change it.
- Risk score = severity × probability × exposure, each factor ≥ 1, score 1..100.
- An uninsurable assessment cannot be attested, linked, or approved against.
- One vote per panelist; only seated panelists vote; a decision is never written by an
  admin arm.
- Payment executes only against a canonical Oracle decision, and at most once per hold.
- Every permissionless crank reads canonical state and cannot choose outcome, payee or
  amount.

## Contract conventions

- Rholang has no imports. Libraries live in `contracts/src/lib/` and are inlined with
  `// @@INLINE:lib/Foo.rho@@`; declare every inlined contract name in the outer `new`.
- One immutable-map state cell per singleton. Reads use `<<-`; mutations consume with `<-`
  and re-post on every path. Never hold a consumed cell across an external await.
- Reply `(true, payload…)` or `(false, reason)`. Reasons are lowercase and stable.
- After value has moved, a refusal must fail the deploy with `1/0`.
- Contracts are published as `rs!(bundle+{*Contract}, *uriCh)` and registered through
  `GenRoot`. Never register an unbundled name.
- Admin payload: `rgen:admin:v1|<domain>|<nonce>|<action>|<arg0>,<arg1>,...`, hashed with
  blake2b256; DER secp256k1 signatures. Admin args are flat strings/ints only.
- Hashes are lowercase hex strings. Money and quality values are integers. No floats.
- Placeholders use `__NAME__` and are limited to the allowlist in
  `tools/check_placeholders.py`.

## Term budgets

- Raw built term ≤ 56 KiB when possible; the node parses at most 64 KiB after minification.
- Depth ≤ 96; contracts per term ≤ 32.
- Do not split a state cell across terms. If a term is too large, move a mutator that
  calls authoritative arms, not the cell.

## Token rules

- Use the native ERTP object API (`rho:rchain:ertp`), not legacy `rho:rchain:makeMint`.
- Only `TokenBook` holds `mint` and `issuer`. It exposes an empty purse via `newPurse`,
  never mint authority.
- The mint crank is permissionless but reads `KAssetBook.mintAuthorization` and records
  `minted` plus a pending reservation.

## Testing

- Every state-mutating arm has a happy path and at least one refusal test.
- Every refusal reason asserted by a suite must exist in source.
- Adversarial coverage is mandatory: unqualified validator, self-validation, double
  validation, revoked credential, non-panelist vote, double vote, double mint, double
  execute, uninsurable link, replay, non-installer register.
- A suite that cannot reach a healthy devnet exits 2 (`not run`), never 0.

## Safety

- Never commit `.devnet/`, private keys, or generated deployment manifests.
- Never run `git add` in the outer home repository; this repository is standalone.
- Do not deploy to a network with value. The contracts are unaudited.
