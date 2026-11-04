# HAZOP of the core primitives

This is the current-core HAZOP. It treats the seven deploy terms as ten nodes and applies fifteen
guide words to each node's parameters. The worksheet is
[`spec/hazop/worksheet.yaml`](https://github.com/rhovision-org/r-gen/blob/main/spec/hazop/worksheet.yaml);
the method is in the [audit charter](audit-charter.md).

## Design intent

| Node | Intent | Invariants | Parameters |
|---|---|---|---|
| `root-install` | Only the installer registers component URIs; keys are unique; versions are positive | L1, L2 | installer, key, URI, version, kind, term order |
| `identity` | One address maps to one identity; only the owner updates it | L1, L2 | address, owner, patch, entry |
| `issuer-credential-proof` | Scoped issuance; non-retroactive one-shot proof | C1–C3, L3 | issuer, subject, scope, status, issuedAt, expiresAt, proof use |
| `claim-validation` | One transition; one K-Asset; eligible validator | C1–C3 | status, validator, deadline, verdict, K-Asset id |
| `kasset-nesting` | State-machine approval; proof authority; forest order | K1–K3 | status, approver, approvedAt, childRefs, proof, scope |
| `value-proposition` | Validate once; caller- and height-bound proof | V1, V2 | status, proposer, caller, atHeight, deadline |
| `oracle` | Decide/execute once; subject-bound application | O1, O2 | adjudicator, subjectRef, decision, execute, evidence, deadline |
| `provenance` | Writer-gated append-only anchors | P1 | assetRef, writers, hash, comment |
| `registries-factories` | Append-only creation; resolvable records | L1, L2 | key, entry, counter, directory/factory state |
| `deployment-phlo` | Correct order and URI binding; private capabilities; bounded cost | L1, L4 | term order, URI binding, private Apply, phlo, install auth |

## Coverage

The worksheet has 150 coverage cells (10 nodes × 15 guide words): 145 are covered by a full row and
five are marked not applicable with a reason. There are 146 rows. Seventy-seven rows are negative
results: the considered deviation has a holding safeguard. Sixty-nine rows have a partial or no
safeguard and therefore name a Lean item (`LR-###`), a Rholang item (`RR-###`), or `accept-risk`.

A negative row is evidence that a specific deviation was considered, not a claim that the node is
safe. The most useful negative results are:

| Safeguard | Evidence |
|---|---|
| A proof take is one-shot | `Proof.take` used flag; `proof_take_once_versioned` |
| Approve refuses the claimant and validator | `KAsset.rho` conflict guard |
| Approve requires an Approver credential and a VP proof | `proveAndCheck` / `checkApprovalVp` |
| Nest refuses same-parent duplicates and cycles | `nestCheck`, `nestProofs` |
| Oracle apply is bound to the case id and the private Apply | `Apply.applyDecision` |
| Anchor hashes are non-empty and unique per record | `Provenance.anchor` |
| Claim comment is open-window only | `Claim.comment` |
| Validate refuses self-validation and late validation | `Claim.validate` |
| Revoke blocks later prove | Credential status guard |
| Duplicate root keys are refused | `GenRoot.register` |
| Install order and placeholders are checked | `install.py` ORDER, dry-run, parse-check |
| A peek is not a commit authority | `check_concurrency.py` |

## Deviations that feed the backlog

The rows below are representative, not the full register. Each has a finding and an action in the
worksheet; the action is either a Lean item in the [rigor roadmap](rigor-roadmap.md) or a Rholang
item in the [improvement plan](rholang-improvements.md).

| HAZOP row | Deviation | Safeguard | Action |
|---|---|---|---|
| `HZ-CLAIM-007` | Unknown verdict maps to Claim `validated` and K-Asset `rejected` | None | RR-04 / RGA-020 |
| `HZ-CLAIM-015` | K-Asset minted before the claim write is complete | None | RR-11 / RGA-032 |
| `HZ-KASSET-003` | Model admits an approver the deployed arm would refuse | Model omits the requirement | LR-01 / RGA-004 |
| `HZ-KASSET-015` | Child proofs consumed before the parent write is acknowledged | No receipt | RR-11 / RGA-033 |
| `HZ-VP-005` | Proof carries a caller-chosen height | Consumers compare height | RR-03 / RGA-021 |
| `HZ-ORACLE-004` | Public open with caller-supplied parties | Adjudicator/Apply binding only | RR-01 / RGA-023 |
| `HZ-ORACLE-015` | Execute spans two contracts without a receipt | Apply refuses a second case application | RR-08 / RGA-024 |
| `HZ-PROV-012` | Anyone can create provenance for any assetRef | None; advisory record | RR-02 / RGA-022 |
| `HZ-ID-011` | Identity and directory writes are not recovery-safe | First-writer-wins only | RR-11 / RGA-031 |
| `HZ-CRED-009` | Deployed prove has no issuedAt lower bound | Expiry guard only | LR-08 / RGA-004 |
| `HZ-DEPLOY-002` | Nest work is unbounded in childRefs | No cap | RR-05 / RGA-025 |
| `HZ-CLAIM-016` | Claim can be born expired or with an impossible comment window | None | RR-07 / RGA-026 |
| `HZ-REG-013` | Registry entry and object state can diverge | None | RR-11 / RGA-031 |

## How to read a row

A row is a deviation from design intent, not a bug report by itself. `safeguard_status: holds`
means the arm or platform check was found and is cited. `partial` means the safeguard narrows but
does not close the deviation. `none` means no safeguard was found for the considered case. The
`action` field is the disposition: a Lean item, a Rholang item, `accept-risk`, or `none` for a
closing safeguard.

## Limits

The HAZOP is qualitative. It does not cover the node's Rholang semantics, phlo accounting, or the
extension primitives. It is not exhaustive over all parameter values; it covers the fifteen guide
words per node and the parameters listed above. A clean coverage cell is a considered
not-applicable, not proof of safety.
