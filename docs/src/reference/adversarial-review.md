# Adversarial review

Reviewed against the `legacy-2026-11-04` tag: the 12-term prototype that passed 12/12
behavioural suites. Passing tests did not make it race-free or Pareto-minimal.

## P0 — representable races or fund loss

| # | Evidence | Defect | Core fix |
|---|---|---|---|
| 1 | `legacy/deploy/40_payments.rho:351-437` | Two `executeCase` callers both peek a hold as `escrowed`, both pay from the shared escrow purse, both stamp the hold. | Removed from core. A payments extension must use a per-hold cell `escrowed → paying → paid`. |
| 2 | `legacy/deploy/40_payments.rho:236-349,370-371` | `executeCase` treats a `pending` hold as success; a deposit landing later is never paid. | Removed from core. Extension must refuse any non-`escrowed` hold. |
| 3 | `legacy/deploy/50_oracle.rho:490-630` | Two `execute` callers both see not-executed; both approve/revoke and pay; both set executed. | Core case consumes `decided → executing → executed`; the subject apply is one-shot; the same-deploy test checks exactly one apply. |
| 4 | `legacy/deploy/21_kasset.rho:684-797` | `markDisputed`/`oracleApprove`/`revoke` accept arbitrary `caseId` + `kassetId`; no subject match; `oracleApprove` can flip revoked → approved. | Public hooks removed. The subject passes a private `applyDecision` capability to the Oracle case; the case stores it in its closure; the subject checks `caseId`. |

## P1 — stale reads and lifecycle corruption

- Mint-after-revoke / missed slash (`legacy/deploy/21_kasset.rho:623-682`,
  `legacy/deploy/12_token.rho:242-428`): removed from core; a receipt extension must make
  mint a one-shot transition against the K-Asset's approval version.
- Permissionless `WorkBook.close` with an arbitrary status
  (`legacy/deploy/20_work.rho:219-257`): removed; the Claim cell's own transitions set
  status.
- `reject` overwrites approved (`legacy/deploy/21_kasset.rho:448-506`): the core K-Asset
  consumes first and only rejects from `validated`/`conditional`.
- `nest` double-links a child (`legacy/deploy/21_kasset.rho:508-621`): the core parent
  consumes first, checks the fresh child list, and appends under the same consume.
- `tally` drops a concurrent vote (`legacy/deploy/50_oracle.rho:386-455`): panels removed;
  the core has one adjudicator.
- Duplicate attestation (`legacy/deploy/30_risk.rho:179-242`): risk removed; a risk
  extension must consume the assessment first and re-check the attester.

## P2 — serialization and dead configuration

- One global state cell per book serialized independent entities. The core uses per-entity
  cells; the only serialization points are identity creation and credential issuance.
- `1/0` after a pending flag relied on whole-deploy rollback. The core uses refusal paths
  and re-posts; it does not use `1/0` for state.
- Stale panel overwrite: panels removed.
- Dead `configs/rgen.json`, orphan `GenAdmin.params`, dead `IdentityBook.nonce`, `holds`
  ignoring `caseId`, negative last share, undocumented 6666 bps threshold: removed with the
  legacy terms.
- "12/12 pass" was not a committed artifact. The core records its verification in
  `docs/src/reference/verification.md`.

## What the legacy did well and the core keeps

- No cell was held across a cross-contract call in the legacy code; the core deliberately
  changes this to consume-first with a documented acyclic call graph.
- Every legacy arm re-posted exactly once; the core keeps this and adds a lint.
- Helpers were not published; the core's `Apply` and `KAsset` library are private.
- Bundles were used correctly; the core keeps `bundle+{*C}` publication.
