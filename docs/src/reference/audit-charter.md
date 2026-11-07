# Audit charter

This page records the method and the boundary of the current-core audit. The machine-readable
record is in [`spec/audit/findings.yaml`](https://github.com/rhovision-org/r-gen/blob/main/spec/audit/findings.yaml),
[`spec/hazop/worksheet.yaml`](https://github.com/rhovision-org/r-gen/blob/main/spec/hazop/worksheet.yaml),
[`spec/proofs/rigor.yaml`](https://github.com/rhovision-org/r-gen/blob/main/spec/proofs/rigor.yaml), and
[`spec/improvements/rholang.yaml`](https://github.com/rhovision-org/r-gen/blob/main/spec/improvements/rholang.yaml).
The checker is `tools/check_audit.py`.

**Status: Phase 1 complete. Phase 2 authorized by the owner; independent technical review has not
been performed.** The review record is `approved` by the owner with that limitation stated. Phase 2
items remain traceable to accepted findings; an external review is still required for any S1.

## Scope

Audited: the seven deploy terms and all 67 deployed arms under `contracts/src`, the Lean model that
claims to describe them, the flow/race manifests, and the current documentation claims.

Not audited: `legacy/` (the tagged pre-Pareto prototype), `crates/` (client tooling), the node's
Rholang implementation, and the economics of the extension primitives (KATs, payments, risk,
panels, governance). The legacy [adversarial review](adversarial-review.md) is not a current-core
review and is labelled as such.

## Baseline evidence

The audit is fixed at `527ed95`. Phase 1 changes manifests, tools, and documentation only. The
`--phase1` checker mode rejects a diff under `contracts/` or `spec/lean/`.

| Artifact | Count |
|---|---|
| Deployed arms dispositioned | 66 |
| Lean Pareto theorems with a claim entry | 39 |
| HAZOP nodes | 10 |
| Guide-word coverage cells | 150 |
| HAZOP rows | 146 |
| Negative rows (safeguard holds) | 77 |
| Rows with partial or no safeguard | 69 |
| Findings | 27 |
| Findings scored P0 / P1 / P2 | 12 / 13 / 2 |
| Proposed Rholang items | 11 |
| Proposed Lean items | 9 |
| Arms with a recorded model/code divergence | 11 |
| Arms with a proved `guard_eq` | 32 |
| Proved-model mutating arms without a `guard_eq` | 0 |
| Read-only proved-model arms | 3 |
| Owed/read-only/infrastructure arms | 30 |

The priority counts follow the severity/likelihood rubric below. They are not a claim that twelve
critical exploits exist; they mean twelve findings cross the rubric's P0 line and need a review
decision before Phase 2.

## Method

1. **Normalize the claim.** Extract a public claim from a README, docs page, contract header, or
   manifest and write it as “for all … if … then …”.
2. **Compare with the theorem.** Read the actual Lean statement, its quantifiers, its premises, and
   its dependencies. Use the verdict vocabulary below.
3. **Compare with the contract.** Read the deployed guard and state write. Record whether the model
   is permissive, stricter, effect-omitting, shape-different, or mixed.
4. **Apply guide words.** For each HAZOP node and parameter, ask what happens under No/Not, More,
   Less, As well as, Part of, Reverse, Other than, Late, Early, Before, After, Duplicate/Replay,
   Stale, Substitute/confused-deputy, and Partial commit.
5. **Disposition.** A holding safeguard becomes a negative row with evidence. A partial or missing
   safeguard becomes a finding and must name a Lean item, a Rholang item, or an explicit risk
   acceptance.

## Claim verdicts

| Verdict | Meaning |
|---|---|
| `proved` | The public claim and the theorem have the same quantifiers, premises, and conclusion. |
| `proved-but-narrower` | The theorem is true and relevant but covers less than the public wording implies. |
| `unproved` | No theorem represents the claim. |
| `overclaim` | Public wording asserts more than the theorem, and the gap is material. |
| `false` | The claim contradicts the model or the deployed code. |

“Proved” always means “proved about the Lean model”. It never means “proved about the deployed
Rholang” in this repository.

## Severity, likelihood, and risk

| Severity | Meaning |
|---|---|
| S1 | Unauthorized authority, forged asset/decision/proof, or a core invariant bypass. |
| S2 | Incorrect authoritative state, core denial of service, or a material proof overclaim. |
| S3 | Bounded misbehaviour, compatibility trap, or an incomplete safeguard. |
| S4 | Documentation, mapping, or quality defect with no direct state effect. |

Likelihood A is an ordinary reachable call; B is crafted input or interleaving; C is a privileged
or unlikely configuration; D is theoretical. Risk is `severity × likelihood` with S1=4 … S4=1 and
A=4 … D=1. P0 when S1 or risk ≥ 9; P1 when 4–8; P2 when ≤ 3. Scores are judgements, not
probabilities.

## Independence and review

The Phase 1 record is not self-approving. The review must name its reviewers, re-derive at least 20%
of the findings (including every S1 and every finding that changes a guard or a public claim), and
mark each finding `accepted`, `rejected`, or `accept-risk`. An auditor must not approve code or
proofs they authored. With one maintainer, the record must state the role separation and the
independence limitation; external review is recommended for any S1.

## Object-capability audit (2026-11-07)

A separate capability-focused pass audits the seven terms as an object-capability system:
the register `spec/audit/capabilities.yaml` (38 rows, 19 `bundle+` expressions, 3 proof kinds,
2 private `Apply` capabilities, 7 ambient system channels), the live suite
`harness/redteam_capabilities.py` (RT-024..RT-037), and the blind run
`spec/hazop/runs/2026-11-07-capabilities/` (36 rows, 9 nodes). The gate is
`tools/check_capabilities.py`; the findings are RGA-048..RGA-069. The public summary is the
[object-capabilities](object-capabilities.md) page.

The pass fixes the K-Asset child anchor (RGA-049), the Root register state order (RGA-061),
`Issuer.authorize` (RGA-048), the K-Asset validator dispute parties (RGA-060), the K-Asset
reply bundle (RGA-050), the issuer registry hold (RGA-069), and the installer/client checks
(RGA-056..RGA-059). It accepts the remaining hazards with a reason in the register and the
run's adjudication. It does not change the charter's boundary: no mechanized Rholang semantics,
no refinement theorem, and no proof of name unforgeability. The Lean model
`RGen.Model.Capability` is an abstract grant/bundle/Apply/proof model, not a capability
semantics.

## What is not claimed

- No mechanized Rholang semantics and no refinement theorem.
- No proof of name/capability unforgeability, chain-height authenticity, JSON schema validity,
  phlo exhaustion, scheduler fairness, or liveness.
- No penetration test. Dynamic evidence is limited to the documented harness suites.
- A negative HAZOP row means the considered deviation had a holding safeguard; it does not mean the
  node is hazard-free.
- Phase 1 is read-only against `contracts/` and `spec/lean/`; it does not fix what it finds.
