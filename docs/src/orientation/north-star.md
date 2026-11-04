# RGen — CoEngineers / Ingenesist

RGen is the first reasonably complete suite of Rholang contracts, paired with a Lean 4 model,
for Dan Robles' **CoEngineers** and **Ingenesist Project** vision. The papers start from a
plain problem: "the value of engineering is invisible" (`@robles2017stewardship p.3`). The
suite makes the work and its validation first-class, durable records.

The handshake is the paper's claim → validation → approval sequence
(`@zhong2019bridge p.4`); the claim is the quantity and the validation the quality
(`@robles2020innovation p.5`):

```
Claim (quantity, work element, selection criteria, clock, comments, value proposition ref)
  -> Validation (quality, qualified validator, evidence)
  -> Approval (acceptable completion, liability)
  -> K-Asset (the claim+validation pair, with approval)
```

A K-Asset is the paper's pairing: "Each pairing forms a single node with two branches
constituting a knowledge asset – 'K-asset'" (`@robles2020innovation p.4`). A ValueProposition
is a separate cell, composable with a claim or K-Asset by reference (`@mathews2017bim p.7`).
An Oracle case resolves a dispute through one credential-proved adjudicator
(`@robles2016nspe p.25`). A Provenance cell keeps the asset's documents and comments with the
asset (`@robles2016nspe p.29`).

The repo is the contracts, the Lean model, and the paper-linked documentation. The core
deliberately does **not** mint, price, transfer, score risk, run panels, or administer a
governance layer. Those are extensions. The [Pareto ledger](../reference/pareto-ledger.md)
states why each primitive is present and what was removed; it is a design test, not the
repo's purpose. The [paper-to-code matrix](../reference/paper-to-code.md) links each core
idea to the contract, the Lean theorem, and the tests.

The design test is: remove the primitive; can the remaining set still express a claim, a
validation, a value proposition and a K-Asset? If yes, it was not core.
