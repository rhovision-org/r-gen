# Claim, validation, K-Asset

A Claim is one linear cell. It carries:

- the claimant and the work element (`titleHash`, discipline, jurisdiction, projectRef);
- the selection criteria (the paper's Talent Pool → Selection Criteria step);
- the statement/definition hashes and the quantity `{unit, value}`;
- the agreed clock (`deadlineHeight`, `commentUntilHeight`) and comment hashes;
- an optional value-proposition reference.

A Validation consumes the open Claim. If the validator holds a credential issued by the
genesis issuer and matching the claim's selection criteria, the claim creates a K-Asset and
transitions to `validated` (or `rejected` for an invalid verdict). A second validation cannot
succeed: the Claim cell is no longer open.

The K-Asset carries the claim+validation pair, the validator's credential, the verdict and
quality, and the approval state. Approval records the approver, conditions, liability and an
`approvalVersion`. A dispute opens an Oracle case with the K-Asset's private
`applyDecision` capability; the case stores that capability, so a decision on one K-Asset
cannot be applied to another.

A ValueProposition is a separate cell: a proposer states a value statement, terms and
beneficiaries; a qualified validator validates it; a K-Asset may reference a validated
value proposition. The papers name the value proposition but define no state machine; the
separate primitive is a user decision recorded in the Pareto ledger.
