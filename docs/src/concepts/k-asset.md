# Claim, validation, K-Asset

The handshake is the paper's claim → validation → approval sequence
(`@zhong2019bridge p.4`); the claim is the quantity and the validation the quality
(`@robles2020innovation p.5`). A Claim is one linear cell. It carries:

- the claimant and the work element (`titleHash`, discipline, jurisdiction, projectRef);
- the selection criteria (the paper's Talent Pool → Selection Criteria step,
  `@zhong2019bridge p.4`);
- the statement/definition hashes and the quantity `{unit, value}`;
- the agreed clock (`deadlineHeight`, `commentUntilHeight`) and comment hashes
  (`@zhong2019bridge p.5`);
- an optional value-proposition reference.

A Validation consumes the open Claim. If the validator holds a credential issued by the
genesis issuer and matching the claim's selection criteria, the claim creates a K-Asset and
transitions to `validated` (or `rejected` for an invalid verdict). A second validation cannot
succeed: the Claim cell is no longer open.

The K-Asset is the pair: "Each pairing forms a single node with two branches constituting a
knowledge asset – 'K-asset'" (`@robles2020innovation p.4`). It carries the claim+validation
pair, the validator's credential, the verdict and quality, and the approval state. Approval
is "an acceptable completion" (`@zhong2019bridge p.4`). Approval records the approver, conditions, liability and an
`approvalVersion`. A dispute opens an Oracle case with the K-Asset's private
`applyDecision` capability; the case stores that capability, so a decision on one K-Asset
cannot be applied to another.

A ValueProposition is a separate cell: a proposer states a value statement, terms and
beneficiaries; a qualified validator validates it; a K-Asset may reference a validated
value proposition. The papers name "the new value proposition" (`@mathews2017bim p.7`) but
define no state machine; the separate primitive is a user decision recorded in the Pareto
ledger. See [the primitive pages](../primitives/k-asset.md).
