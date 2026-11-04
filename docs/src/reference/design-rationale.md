# Design rationale

Why the Rholang is written the way it is. Rows marked **RGen** are engineering decisions
with no paper basis; they must not be presented as paper-derived.

## Concurrency

| Construct | Why | Basis |
|---|---|---|
| One linear state cell per entity (Claim, K-Asset, Credential, ValueProposition, OracleCase, Provenance, Identity) | Two operations on the same entity cannot both observe the same pre-state. The cell consume serializes them; the loser sees the post-state and refuses. | RGen |
| Consume-first (`for (@s <- state)`) in every mutating arm | All guards are evaluated after the consume. A peek-then-commit pattern is TOCTOU by construction; this was the legacy P0 defect. | RGen |
| Read arms use `<<-` (peek) | Reads never block writers and never mutate. | RGen |
| Exactly one re-post per consume path | A missing re-post deadlocks the entity; a double re-post creates two states. `tools/check_concurrency.py` checks this structurally. | RGen |
| Private `Apply.applyDecision` capability | The Oracle case stores the subject's capability in its closure, never a caller-supplied id. A decision cannot be applied to another K-Asset. | RGen + `@robles2016nspe p.25` |
| Parent-owned nesting edges with `(approvedAt,id)` order | Cycles are non-representable without graph traversal; duplicate children are refused under the parent's consume. | RGen + `@zhong2019bridge p.6` |
| No global nonce cell | IDs are registry URIs; no global counter serializes creation. | RGen |
| Compile-time factory wiring | Core terms resolve factory URIs at install, not per call. Root is a client directory only. | RGen |
| Identity directory and credential registry are the only serialization points | Identity creation is first-writer-wins; credential issuance is registered once. Neither is on the claim/validation hot path. | RGen |

The declared serialization points are `rootState`, `directoryState`, `issuerState`, and `factoryState`.

**Consume-first liveness.** Holding a consumed cell across a cross-contract call is safe only
if the call graph is acyclic. The only cross-entity acquisitions are: Claim.validate creates
a K-Asset (new cell); K-Asset.openDispute creates an Oracle case (new cell); Oracle.execute
calls the subject's private apply (case → subject). There is no reverse edge: openDispute
creates a case and never consumes one, and the subject never calls the case. The concurrency
lint and the same-deploy tests enforce this.

## Paper-derived process choices

| Construct | Why | Basis |
|---|---|---|
| Claim = quantity/definition; validation = quality/characteristics | The paper's definition of the two halves | `@robles2020innovation p.5` |
| Claim → validation → approval | The Bridge paper's handshake and "acceptable completion" | `@zhong2019bridge p.4` |
| K-Asset created on validation | The claim+validation pair is the K-Asset | `@robles2020innovation p.4-5` |
| Credential gate before validation, approval, adjudication | "permissioned by qualifications"; credentials before events | `@mathews2017bim p.7`; `@zhong2019bridge p.6` |
| Single adjudicator proved by a credential | "the most appropriate person" | `@robles2016nspe p.25`; `@robles2016naic p.9`; `@mathews2017bim p.8` |
| Per-asset provenance cell with anchors/comments | The asset keeps its own information; sealing | `@robles2016nspe p.29`; `@zhong2019bridge p.3,p.6` |
| Clock and comment window on the claim | The paper's agreed clock and stakeholder comment period | `@zhong2019bridge p.5` |
| Selection criteria on the claim | Figure 1: Talent Pool → Selection Criteria → Work Element | `@zhong2019bridge p.4` |
| Liability recorded on approval/decision | "assign, limit, or transfer liability"; risk-transfer points | `@robles2016nspe p.25`; `@zhong2019bridge p.6` |

## User decisions (not paper-derived)

| Construct | Why |
|---|---|
| Separate ValueProposition cell | The user asked for a first-class value proposition. The papers name the phrase but define no state machine; the ledger labels this `paper-adjacent / user decision`. |
| No token, pricing, payments, risk, panels, admin, handles in core | The user's Pareto boundary and the instruction that tokenisation/pricing is not primary. |
| REV address as identity; no handles | Removes the global handle-uniqueness race. |

## Explicit non-goals

- The core does not mint, price, or transfer anything.
- The core does not call an extension. Extensions read core facts by URI/capability.
- The core does not claim "maximal concurrency" absolutely. It claims: **no shared mutable
  cell across independent entities; one writer per entity**; independent-entity transitions
  do not serialize. Within one entity, serialization is inherent and intentional.
