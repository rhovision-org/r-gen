# @zhong2019bridge — A New Perspective of Accelerated Bridge Construction

## p.3 — provenance and ownership

> "their provenance and ownership"

**Why it matters.** The provenance cell anchors document hashes to the asset; the asset is
the keeper of its own information.

## p.4 — the handshake and Figure 1

> "'Claim' and 'Validation' represent a key mechanism i.e. the 'handshake'."
>
> "'Approval' represents an acceptable completion."

**Why it matters.** The core is claim → validation → approval. The Claim cell carries the
work element and selection criteria from Figure 1; the K-Asset carries the validation and
approval.

## p.5 — clock and stakeholder comments

> "pre-defined and agreed upon 'clock' embedded in the blockchain and all participants can
> see the specific actions to be taken and their status"

**Why it matters.** The core carries `deadlineHeight` and `commentUntilHeight` on the Claim
cell, and records comment hashes on the claim, not in a detached global book.

## p.6 — nesting and risk transfer

> "'Blocks' on a blockchain are nested in this manner as well."
>
> "Tokens issuance marks points where risk is transferred from one party to another."

**Why it matters.** K-Asset nesting is parent-owned and ordered; the core records approval
and liability data without minting. A receipt extension may read the approval event if it
chooses the Bridge mint timing.
