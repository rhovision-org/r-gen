# Oracle

## Paper anchors

> "the adjudicator is deemed the most appropriate person to be performing the adjudication."
> — `@robles2016nspe p.25`

> "An Oracle contract is an adjudicated contract…" — `@robles2016naic p.9`

> "An Oracle contract is an adjudicated contract with the added requirement the adjudicator
> … is deemed the most appropriate person" — `@mathews2017bim p.8`

## What the paper means

An oracle case has one named adjudicator, chosen because they are the most appropriate person,
not a weighted panel. The adjudicator must prove a credential at decision time. The decision is
applied to the subject through the subject's own capability.

## How the Rholang expresses it

- `contracts/src/deploy/30_oracle.rho` — `OracleFactory@"open"` checks the adjudicator
  credential by registry URI and requires its subject to match the named adjudicator.
- `OracleCase@"decide"` consumes `caseState`, uses the stored
  `adjudicatorCredentialUri`, calls `Credential@"prove"`, takes/checks the proof, and records
  the decision.
- `OracleCase@"execute"` is two-phase (`decided → executing → executed`), re-posts before
  calling the subject's private `applyDecision`, and is one-shot.
- `OracleCase@"expire"` and `@"close"` guard the terminal paths.

## What the Lean proves

- `RGen.O1_execute_bound_once` — execution is subject-bound and one-shot.
- `RGen.O2_close_finished` — closing requires executed/expired.
- `RGen.OracleState.decide_once`, `decide_requires_proof`,
  `execute_subject_bound`, `execute_once`, `close_open_refused`.
- Pair matrix: `oracle_decide_expire_two_way`, `oracle_execute_execute_never_after`,
  `oracle_decide_evidence_never_after`.

## Deliberately excluded

Panels, voting, tallying, random selection, and fund/payment execution are extensions. The
core has one adjudicator and no payment arm.

## See also

- [K-Asset](k-asset.md), [Value proposition](value-proposition.md)
- [Race-freedom proof](../reference/race-freedom-proof.md)
- Suite: `harness/unit_oracle.py`
