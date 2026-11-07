# Guard conformance bridge

> **Run:** `make guard-check`
> **Manifest:** `spec/guards/arms.yaml`
> **Checker:** `tools/check_guard_bridge.py`

The Lean proofs are proofs about `spec/lean`, not about the deployed Rholang. The guard bridge is
the smallest useful link between the two: for each changed mutating arm it checks that the
canonical guard/refusal atoms still appear in the deployed source, that the flow manifest still
names the arm, and that a `guard_eq` theorem exists or is explicitly `owed`.

## What it checks

- **Source atoms.** Each arm lists the exact guard expressions and refusal strings that the
  contract must contain. The checker normalizes whitespace and requires every atom.
- **Flow entry.** `spec/flows/core.yaml` must still contain the contract/arm pair.
- **Guard theorem.** A named `guard_eq` must exist in `RGen/ArmGuards.lean`; otherwise the arm is
  marked `owed` and the run reports it.

## What it does not prove

- It does not parse or evaluate the Rholang guard. It is a drift check over a hand-maintained
  atom list, not a semantics-preserving extraction.
- It does not prove the Lean guard is equivalent to the deployed guard. The existing `guard_eq`
  theorems are model guards; the new reservation, mint, deadline and proof guards are covered by
  the new Lean modules (`IdentityReservation`, `ClaimMint`, `Deadline`, `ProofCapability`,
  `NestCrash`, `System`).
- It does not cover arms whose `guard_eq` is `owed`. Those are listed as warnings:
  `identity.resume`, `claim.create`, `claim.resume`, `credential.issue`, `oracle.open`,
  `provenance.create`.

## Reproduce

```bash
make guard-check
```

The checker fails if an atom disappears from the source or a flow entry is removed. It prints
warnings for owed theorems rather than turning them into a pass.
