# @robles2020innovation — The Innovation Bank (IMECE2020-23015)

## p.3 — risk = S × P × E

> "Risk = f(S, P, E). Specifically, Risk = S × P × E where specific values for SPE are
> ranked on an integer scale, with 1 representing slight … to 100."

**Why it matters.** The risk model is paper-derived, but it is an application extension in
RGen, not part of the core claim/validation primitive.

## p.4 — K-Asset pairing and receipt

> "Each pairing forms a single node with two branches constituting a knowledge asset –
> 'K-asset' – which is memorialized by the creation of an electronic token awarded to each
> participant in a pair."

**Why it matters.** This is the definition of the K-Asset and the reason the Claim cell
creates a K-Asset on validation. The receipt is tokenisation; the core does not mint.

## p.5 — claim is quantity, validation is quality

> "The claim serves as the quantity (definition) and the validation serves as the quality
> (characteristics)."

**Why it matters.** The Claim cell carries `quantity`, `statementHash`, and
`definitionHash`; the Validation carries quality and the evidence hash. It also shows the
paper's mint timing: the receipt is produced when the pair forms, at validation. RGen's
core does not mint; the receipt extension must choose validation (this paper) or approval
(the Bridge paper).

## p.6-7 — WIKiD

> "6. THE WIKiD TOOLS ALGORITHM"

**Why it matters.** WIKiD is a valuation/measurement model, not a claim/validation state
machine. It is deferred as a metric extension and is not a core primitive.
