# Status and limits

**Devnet-only, unaudited, no real value.**

## Verified on 2026-11-04

- All twelve rendered terms parse with the pinned rholo parser.
- A fresh rholo devnet (node `e2d073d`, 8 GB isolated `rgen-bootstrap`) installed all
  twelve terms and ran every implemented behavioural suite:
  `root, identity, credentials, work, kasset, provenance, token, risk, oracle, journey,
  adversarial, conservation` — **12/12 pass**.
- The component catalogue is acyclic; state cells are unique.
- The static gates cover placeholders, integer-only money, bundled publication, suite
  wiring, flow arms and arithmetic vectors.
- `cargo test -p rgen-core` passes; the Rust workspace type-checks against the pinned
  r-cash and rholo crates.

## Implemented and exercised by the harness

- Identity and handle uniqueness.
- Credential issuance, scope matching, expiry, revocation and pool selection.
- Work, claims, amend, withdraw and quantity validation.
- K-Asset validation, approval, rejection and nesting.
- KAT mint-once, balances, reputation, transfer and conservation.
- SPE risk, insurability, attestation and the uninsurable refusal.
- Oracle open, empanel, vote, tally, execute and close, with non-panelist and double-vote
  refusals.

## Owed

- Funded r-cash escrow release/refund (`unit_payments`). The r-cash rail was not installed
  on the verification devnet, so this path is deployed but unexercised.
- Dispute bond split and `revokeEarned` slashing (`unit_dispute`).
- Lean models and the flow-to-theorem map.
- Metcalfe/CAPM valuation metrics.
- Web client.

## Honest limits

- The panel selection is deterministic but the on-chain subject ordering is not a
  cryptographic random beacon.
- Extreme-risk approval checks that an oracle case id is present; it does not yet verify
  the decision inside the approval arm (the execution arm does verify it).
- Payment execution is non-atomic across steps by design; each step is idempotent and
  retryable.
