# The azoth claim bundle

A calculation run emitted by `python -m azoth.rgen` in the azoth checkout at commit
`36e05d37`, on the Rust backend, validated by the Python backend.

The calculation is `eos.antoine_vapor_pressure` at methane's 150 K worked example. It is a
`verified` calculation in azoth's provenance, and its five declared cases are the spec's
three reference tests plus the worked example and the external i-pentane case. All five
pass on both backends, so the claim's quantity is five validated cases.

The files are generated, not edited. Their hashes name the azoth build and the case set, so
they move when either moves; that is the point. To regenerate them:

```sh
cd /path/to/azoth
python -m azoth.rgen bundle \
  --calc eos.antoine_vapor_pressure \
  --inputs /tmp/antoine.json \
  --out /path/to/r-gen/harness/demo/artifacts/azoth \
  --project azoth-demo --jurisdiction US-TX \
  --claim-backend rust --validation-backend python
```

`payloads/claim.json` carries `deadlineHeight: 0` and `payloads/validation.json` carries an
empty `credentialUri`. Both are placeholders: the harness substitutes the current height and
the validator's credential before deploying. The contract refuses a zero deadline and an
empty credential, so an unsubstituted bundle fails rather than filing a claim with no clock.
