# Bridge inspection walkthrough

1. **Identity.** Alice registers a profile under her REV address.
2. **Qualification.** The genesis issuer issues Bob a `Validator` credential for
   `structural` / `US-TX` at level 2, and Carol an `Approver` credential.
3. **Work.** Alice opens `bridge-deck-inspection` and claims twelve inspections at a hold
   point, with a statement and definition hash.
4. **Validation.** Bob validates the claim, scoring completeness, correctness,
   traceability and fitness. The K-Asset is `validated`.
5. **Risk (optional).** A risk assessor records `S×P×E`, answers the exposure,
   probability and consequence questions, and a second assessor attests.
6. **Approval.** Carol approves. The K-Asset becomes `approved`.
7. **Receipt.** Anyone can crank the mint. Alice and Bob receive KAT; the mint is recorded
   once.
8. **Adjudication (optional).** If a party disputes, a qualified panel votes. A rejected
   or partial outcome can revoke the K-Asset and instruct payment through r-cash.

The harness runs this path in `harness/unit_journey.py`.
