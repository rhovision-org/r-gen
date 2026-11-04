# K-Asset

## Paper anchors

> "Each pairing forms a single node with two branches constituting a knowledge asset –
> 'K-asset' – which is memorialized by the creation of an electronic token awarded to each
> participant in a pair." — `@robles2020innovation p.4`

> "The claim serves as the quantity (definition) and the validation serves as the quality
> (characteristics)." — `@robles2020innovation p.5`

> "'Approval' represents an acceptable completion." — `@zhong2019bridge p.4`

> "'Blocks' on a blockchain are nested in this manner as well." — `@zhong2019bridge p.6`

## What the paper means

The claim+validation pair is the K-Asset. Approval is a separate, qualified act after
validation. K-Assets can be nested; the core records the nesting order and the approval data
without minting a token.

## How the Rholang expresses it

- `contracts/src/deploy/20_claim.rho` calls `makeKAsset` from `finalizeValidation`; the
  K-Asset library is in `contracts/src/lib/KAsset.rho`.
- `KAsset@"approve"` requires validated/conditional, a non-claimant, non-validator approver,
  a credential proof, and (when a VP is referenced) a validated VP proof.
- `KAsset@"reject"` requires the same qualification and records the rejection.
- `KAsset@"proveApproved"` creates a one-shot approval proof.
- `KAsset@"nest"` is two-phase: a read-only pre-pass, child `proveApproved` proofs, then a
  consume of the parent and a final duplicate/scope/order check.
- `KAsset@"openDispute"` passes the private `Apply` capability to an oracle case.

## What the Lean proves

- `RGen.K1_approve_credential` — the credential proof subject is the approver.
- `RGen.K2_approve_status` — approval is only from validated or conditional.
- `RGen.K3_nest_acyclic` — strict order and no nesting cycle.
- `RGen.KAssetState.approve_requires_vp_proof`,
  `approve_by_claimant_refused`, `reject_requires_credential_proof`,
  `nest_child_below_parent`, `nest_child_scope`.
- Pair matrix: `kasset_approve_reject_two_way`,
  `kasset_openDispute_proveApproved_never_after`,
  `kasset_nest_same_never_after_arm`.

## Deliberately excluded

KAT/receipt minting, pricing, liability accounting, and token transfer are extensions. The
core records approval and nesting facts; an extension can mint when it chooses validation or
approval as its receipt timing.

## See also

- [Claim](claim.md), [Validation](validation.md), [Oracle](oracle.md)
- [Paper-to-code matrix](../reference/paper-to-code.md)
- Suites: `harness/unit_kasset.py`, `harness/integration_core.py`
