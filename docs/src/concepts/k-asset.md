# The K-Asset

A K-Asset is a claim paired with a validation, memorialized by a KAT receipt to each
participant and ordered in time by the chain.

```
Work Element -> Claim (quantity, by claimant)
                    -> Validation (quality, by qualified validator)
                    -> Approval (by a qualified approver or oracle)
                    -> K-Asset + KAT receipts
```

- The claim carries a statement hash, definition hash, quantity `{unit, value}`, evidence
  and optional risk reference.
- The validation carries a verdict (`valid`, `partial`, `invalid`), four quality
  dimensions each 1..5, evidence and the validator's credential at the event height.
- The approval carries a decision, conditions, liability and optional risk/oracle case.
- The receipt is minted once, after approval. Nesting approved K-Assets creates a composed
  asset and mints nothing.

Reputation is **net lifetime earned KAT**. KAT balances are transferable; `earned` is not.
Buying KAT buys no validation weight.
