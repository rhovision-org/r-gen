# Bridge inspection walkthrough

1. Alice registers an identity under her REV address.
2. The genesis issuer issues Bob a `Validator` credential and Carol an `Approver` credential.
3. Alice proposes a value proposition for the inspection and Bob validates it.
4. Alice creates a claim: twelve deck inspections, a statement hash, a definition hash, a
   selection criterion for `Validator`/structural/US-TX, a clock and a comment window.
5. Bob validates. The Claim cell creates the K-Asset and becomes `validated`.
6. Carol approves. The K-Asset becomes `approved`; the approval records liability and an
   approval version. No token is minted.
7. If a party disputes, the K-Asset opens an Oracle case with its private apply capability.
   Dave, the named adjudicator with an `Oracle` credential, decides. Execution calls the
   K-Asset's private apply; the K-Asset becomes `upheld` or `revoked`.
8. Alice creates a provenance cell for the K-Asset and anchors the inspection report. The
   anchor is immutable; `verify` recomputes the anchor's presence.

The harness runs this path in `harness/unit_core.py`; the same-deploy race suite is
`harness/concurrency_core.py`.
