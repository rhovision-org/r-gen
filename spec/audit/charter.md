# r-gen core audit charter

Status: Phase 1 (read-only) baseline `527ed95`.
Scope: the seven deploy terms and every deployed arm under `contracts/src`, plus the Lean model
under `spec/lean` that claims to describe them. `legacy/` and `crates/` are out of scope.

## Purpose

The audit answers four questions with evidence rather than assertion:

1. What do the deployed primitives actually do at their trust boundaries?
2. What do the Lean theorems actually state, and how far is that from the public claims?
3. Where does the model diverge from the Rholang, and in which direction?
4. Which deviations and proof gaps need a Lean theorem, a Rholang fix, a test, or explicit risk
   acceptance?

The HAZOP is the elicitation front-end for the proof backlog. A deviation whose safeguard is
partial or absent must name a Lean item (`LR-###`), a Rholang item (`RR-###`), or an explicit
`accept-risk` decision. Silence is not a safeguard.

## Independence

The auditor must not approve code or proofs they authored. If the same maintainer wrote both, the
record must say so, and a second reviewer must independently re-derive at least 20% of the findings,
including every S1 and every finding that changes a guard or a public claim. The review record lives
in `spec/audit/findings.yaml` under `review`.

Phase 1 is read-only with respect to `contracts/` and `spec/lean/`. Changes to manifests, tools,
and documentation are allowed because they do not alter deployed behaviour or proofs.

## Evidence standard

Every finding has:

- an ID (`RGA-###`) and a one-line title;
- `file:line` evidence, or a theorem/declaration name plus its module;
- a plain-language statement with explicit quantifiers and premises;
- a reproducible command where the claim is dynamic, or the exact static argument where it is not;
- a severity, likelihood, risk score, and disposition.

Documentation, comments, and manifest statuses are claim sources, not evidence. A `proved-model`
label is a claim to be audited, not a proof of deployed behaviour.

## Claim verdicts

Public claims are normalized to “for all … if … then …” and compared with the actual Lean
statement. The verdict vocabulary is:

| Verdict | Meaning |
|---|---|
| `proved` | The public claim and the theorem have the same quantifiers, premises, and conclusion. |
| `proved-but-narrower` | The theorem is true and relevant, but covers less than the public wording implies. |
| `unproved` | The claim is not represented by any theorem. |
| `overclaim` | Public wording asserts more than the theorem, and the difference is material. |
| `false` | The claim contradicts the model or the deployed code. |

“Proved” always means “proved about the Lean model”. It never means “proved about the deployed
Rholang” in this repository.

## Severity and likelihood

Severity:

- **S1** — unauthorized authority, forged asset/decision/proof, or a bypass of a core invariant.
- **S2** — incorrect authoritative state, core denial of service, or a material proof overclaim.
- **S3** — bounded misbehaviour, a compatibility trap, or an incomplete safeguard.
- **S4** — documentation, mapping, or quality defect with no direct state effect.

Likelihood:

- **A** — ordinary reachable call with normal inputs.
- **B** — crafted input, crafted interleaving, or a deliberately chosen parameter.
- **C** — privileged, installer, or unlikely configuration.
- **D** — theoretical, or requires breaking the platform assumptions.

Risk is a 1–16 judgement (`severity × likelihood`, with S1=4 … S4=1 and A=4 … D=1). P0 when S1 or
risk ≥ 9; P1 when 4–8; P2 when ≤ 3. Scores are judgements, not measurements, and must not be
presented as probabilities.

## Assumptions ledger

The following are assumptions of the model or the deployment, not proved results:

- `Run` is a finite list of events in trace order; there is no scheduler, fairness, or interleaving
  enumeration.
- `Event.apply` is deterministic and pure; Rholang COMM semantics, name unforgeability, and
  single-use cells are cited, not modelled.
- Arm steps are hand-transcribed from the contracts; no mechanized extraction or refinement exists.
- Heights are supplied by `rho:block:data`; the model does not prove chain-height authenticity.
- Proofs are modelled as data plus a one-shot cell; the deployed proof is a private `Proof`
  capability obtained by resolving a URI.
- Phlo, deploy depth, serialization size, and JSON shape are deployment concerns with no model.
- The arm-to-model map is checked by name and cell, not by guard equivalence.

## Gate rules

- `tools/check_audit.py --strict` must pass before the Phase 1 review.
- No Phase 2 Lean or Rholang change may cite a finding whose `review.status` is not `approved`.
- Every HAZOP row with `safeguard_status: partial` or `none` must name an `LR-###`, `RR-###`, or
  `accept-risk` action.
- Every public theorem cited in docs must exist and be in the axiom audit ledger.
- The audit record must state what was not examined. A clean result for a node means the considered
  deviations were dispositioned, not that the node is hazard-free.
