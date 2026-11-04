# RGen Pareto core

RGen expresses the papers' engineering handshake as the smallest set of state machines that
can carry it:

```
Claim (quantity, work element, selection criteria, clock, comments, value proposition ref)
  -> Validation (quality, qualified validator, evidence)
  -> Approval (acceptable completion, liability)
  -> K-Asset (the claim+validation pair, with approval)
```

A ValueProposition is a separate cell, composable with a claim or K-Asset by reference. An
Oracle case resolves a dispute through one credential-proved adjudicator. A Provenance cell
keeps the asset's documents and comments with the asset.

The core deliberately does **not** mint, price, transfer, score risk, run panels, or
administer a governance layer. Those are extensions. The Pareto ledger
(`reference/pareto-ledger.md`) states why each primitive is present and what was removed.

The design test is: remove the primitive; can the remaining set still express a claim, a
validation, a value proposition and a K-Asset? If yes, it was not core.
