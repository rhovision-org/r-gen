# Paper-to-code matrix

One row per core idea: paper key and page, the quoted claim, the Rholang expression, the Lean
theorem, and the behavioural/corpus tie. This is the extensive linkage between the Robles
papers and the Pareto core. The core rows are anchored in `@robles2020innovation p.4`,
`@robles2020innovation p.5`, `@zhong2019bridge p.4`, `@zhong2019bridge p.6`,
`@robles2016nspe p.29`, and `@mathews2017bim p.7`.

| # | Paper | Page | Quoted idea | Rholang | Lean | Tie |
|---|---|---|---|---|---|---|
| 1 | `@robles2016nspe` | p.40 | Records/identity context | `10_identity.rho`: `IdentityFactory@"create"`, `IdentityDirectory@"lookup"` | `Directory.create_unique`, `update_owner_requires_owner` | `unit_identity.py` |
| 2 | `@zhong2019bridge` | p.4 | "Talent Pool -> Selection Criteria"; the handshake | `10_identity.rho` + `20_claim.rho`: identity lookup, claim `selectionCriteria` | `Directory.create_unique`, `ClaimState.validate_requires_subject` | `unit_claim.py` |
| 3 | `@mathews2017bim` | p.7 | "Permissioned by Qualifications" | `11_credentials.rho`: `Credential@"prove"`; `20_claim.rho` / `22_value.rho` / `lib/KAsset.rho` / `30_oracle.rho` proof gates | `C1_prove_requires_active`, `core_arm_authority`, `proof_take_once_versioned` | `unit_credentials.py`, `unit_claim.py` |
| 4 | `@zhong2019bridge` | p.6 | "validation of credentials should be in place before validation of events" | `20_claim.rho`: `Claim@"validate"` resolves and proves the credential before the claim commit | `C2_revoke_blocks_prove`, `ClaimState.validate_once` | `unit_claim.py` |
| 5 | `@robles2016nspe` | p.25 | "the adjudicator is deemed the most appropriate person" | `30_oracle.rho`: `OracleFactory@"open"` stores the adjudicator credential; `OracleCase@"decide"` proves it | `OracleState.decide_requires_proof`, `decide_once` | `unit_oracle.py` |
| 6 | `@robles2016naic` | p.9 | "An Oracle contract is an adjudicated contract" | `30_oracle.rho`: one adjudicator, no panel | `O1_execute_bound_once`, `O2_close_finished` | `unit_oracle.py` |
| 7 | `@robles2020innovation` | p.4 | "claim+validation pair = K-Asset" | `20_claim.rho`: `finalizeValidation` calls `makeKAsset`; `lib/KAsset.rho` | `claim_validation_exactly_one_kasset`, `approval_composes_credential_and_vp_proofs` | `unit_core.py`, `integration_core.py` |
| 8 | `@robles2020innovation` | p.5 | "claim serves as the quantity … validation serves as the quality" | `20_claim.rho`: `quantity`, `statementHash`, `definitionHash`, quality/evidence in validation | `ClaimState.validate_creates_exactly_one_kasset` | `unit_claim.py`, corpus `V1-*` |
| 9 | `@zhong2019bridge` | p.4 | "'Approval' represents an acceptable completion" | `lib/KAsset.rho`: `KAsset@"approve"` requires credential + VP proofs | `K1_approve_credential`, `K2_approve_status` | `unit_kasset.py` |
| 10 | `@zhong2019bridge` | p.5 | "pre-defined and agreed upon 'clock'" | `20_claim.rho`: `deadlineHeight`, `commentUntilHeight`; `Claim@"comment"` window | `ClaimState.validate_within_deadline`, `comment_within_window` | `unit_claim.py` |
| 11 | `@zhong2019bridge` | p.6 | "'Blocks' … are nested"; risk transfer | `lib/KAsset.rho`: two-phase `KAsset@"nest"`, child `proveApproved` proofs | `K3_nest_acyclic`, `nest_child_below_parent`, `nest_child_scope` | `unit_kasset.py` |
| 12 | `@mathews2017bim` | p.7 | "the new value proposition" | `22_value.rho`: `ValuePropositionFactory@"propose"` now requires quantity, quality and variance; `@"validate"`, `@"proveValidated"` | `V1_validate_once`, `proveValidated_requires_validated`; [variance model](variance-model.md) | `unit_value.py` |
| 13 | `@mathews2017bim` | p.8 | adjudicator as the most appropriate person | `30_oracle.rho`: stored adjudicator credential | `OracleState.decide_requires_adjudicator` | `unit_oracle.py` |
| 14 | `@mathews2017bim` | p.9 | "new value proposition … intrinsic intangible value" | `22_value.rho`: validated/disputed/upheld value proposition cell | `V2_dispute_blocks_prove`, `openDispute_requires_status` | `unit_value.py` |
| 15 | `@robles2016nspe` | p.29 | "The asset becomes the keeper of its own information" | `40_provenance.rho`: per-asset anchors/comments/verify | `P1_anchors_append_only`, `anchor_unique`, `verify_monotone` | `unit_provenance.py` |
| 16 | `@zhong2019bridge` | p.3 | "provenance and ownership" | `40_provenance.rho`: `assetRef`, writer list, anchor hashes | `P1_anchors_append_only` | `unit_provenance.py` |
| 17 | `@robles2020innovation` | p.5 | receipt timing at validation | `20_claim.rho`: validation creates the K-Asset; no mint in core | `claim_validation_exactly_one_kasset` | `integration_core.py` |
| 18 | engineering infrastructure | — | creation registries and identity directory | `11_credentials.rho`, `20_claim.rho`, `22_value.rho`, `10_identity.rho` | `Registry.verify_monotone`, `Directory.create_unique` | `unit_identity.py`, `unit_credentials.py` |

## Not mapped to a core primitive

- `@robles2017stewardship p.3` — reputation/Quant and the invisibility thesis. Background for
  why claim and validation are first-class; tokenisation and reputation are extensions.
- `@robles2020innovation p.3` — Risk = S×P×E. Deferred risk extension; the variance-as-risk
  bridge is the [variance model](variance-model.md), consumed by r-sure, not by the core.
- `@robles2020innovation p.6-7` — WIKiD tools. Deferred metrics extension.
- `@robles2016naic p.4`, `@robles2016nspe p.14` — insurability questions. Deferred risk
  extension.
- `@caase2018agenda` — included but uncited; not a source for a core primitive.

## Reading the columns

- **Rholang** names the deploy term/arm or the private library arm. The `// Paper:` header in
  each term carries the same page cites.
- **Lean** names the essential theorem from `spec/lean/RGen/Pareto.lean` and the per-primitive
  model. The proof is model-level; see [Race-freedom proof](race-freedom-proof.md).
- **Tie** is a behavioural suite or corpus row. It is finite evidence, not refinement.

## Code-header citation index

`@mathews2017bim p.7`, `@mathews2017bim p.8`, `@robles2016naic p.9`, `@robles2016nspe p.25`, `@robles2016nspe p.29`, `@robles2016nspe p.40`, `@robles2020innovation p.4`, `@robles2020innovation p.5`, `@zhong2019bridge p.3`, `@zhong2019bridge p.6`
