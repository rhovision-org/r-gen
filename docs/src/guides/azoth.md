# Filing an azoth calculation

An engineering calculation from the
[azoth](https://github.com/PatrickMockridge/Azoth) library can be filed as a claim on
r-gen. The claim carries the calculation's spec and result as hashes; a second actor
validates it with a credential; the pair becomes a K-Asset; and the documents are anchored
to the asset's provenance cell.

This is the paper's handshake applied to a computed number: the claim is the quantity
(`@robles2020innovation p.5`), the validation is the quality, and the asset keeps its own
information (`@robles2016nspe p.29`).

## The bundle

`python -m azoth.rgen bundle` writes a directory. Seven documents form a DAG, each naming
its parent by hash:

| document | what it says |
|---|---|
| `definition` | the spec and both implementations, with hashes |
| `build` | the git commit, the versions, and a clean tracked tree |
| `statement` | the run's inputs, backend and result, with the result's provenance block |
| `cases` | the spec's case set and the external oracle cases, replayed on both backends |
| `agreement` | the two implementations' field-by-field comparison |
| `quality` | the four scores and the counts they came from |
| `validation-evidence` | the verdict, the scores and the comment |

The files under `payloads/` are the on-chain shapes: `claim.json`, `validation.json` and
`anchors.json`. They are integer-only, because r-gen's renderer has no floats.

The claim's quantity is the number of validated cases, not the computed magnitude. The
result itself - for example a vapour pressure in pascals - is in the anchored statement.
The chain carries how many cases stood behind it.

## What is validated

Correctness is measured against each case's **expected values**: the external NeqSim
oracle cases the azoth library records, not the other implementation. Two implementations
of the same spec agreeing is completeness; it is not evidence that the physics is right.

The validator's four scores are the ones `kasset.conventions/v1` names. Their derivation
is in the quality document, so a consumer can recompute them.

## Deploying

The harness is `harness/azoth_claim.py`. It re-hashes every document, checks the payloads
with the SDK's own structural rules (`rgen-cli validate-payload`), and then:

1. issues the validator a `Validator` credential matching the claim's selection criteria;
2. substitutes the deadline height and the credential URI - the only two values the bundle
   leaves for the deployer;
3. creates the claim with the **claimant's** key and validates it with the **validator's**
   key; the contract refuses a validator equal to the claimant;
4. creates a provenance cell bound to the K-Asset and anchors the seven documents in
   parent-before-child order;
5. re-reads the anchor list and calls `verify` for every hash.

With `--approve`, a third key and an `Approver` credential approve the K-Asset.

```sh
make demo-azoth          # the committed bundle, on a running devnet
make demo-azoth-verify   # re-read every URI and relationship
make unit-azoth          # the offline checks, then the live path if a devnet answers
```

## The demo bundle

`harness/demo/artifacts/azoth/` holds `eos.antoine_vapor_pressure` at methane's 150 K
worked example, generated at azoth commit `36e05d37`. Its five declared cases pass on both
backends, so the claim's quantity is five validated cases. The files are generated, not
edited; their README states the regeneration command, and their hashes move when the azoth
build or the case set moves.

## Limits

- **Devnet only.** No token is minted and no price is set.
- **The validator's independence is implementation-level in this demo.** The claimant's key
  and the validator's key are distinct, and the contract checks that; the runs are the Rust
  and Python implementations of the same spec. The independent evidence is the external
  oracle case set. A production validator runs the bundle on its own checkout.
- **The bundle is emitted off-chain.** r-gen signs and deploys it; azoth has no dependency
  on r-gen and holds no key.
- **A record-list calculation is refused** by the emitter, with the calc id and the field,
  rather than silently flattened. Models and flowsheet runs are separate claim units.
