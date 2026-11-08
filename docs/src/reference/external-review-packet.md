# External review packet

This page is the reviewer-facing entry point for the two S1 residuals and the P0 set. It
does not replace the [close-out ledger](closeout.md) or the audit charter; it collects the
evidence and the questions a reviewer needs.

## Scope

- **RGA-051 (S1, risk-accepted):** the client trusts an unsigned manifest Root URI. Root
  pinning is implemented and tested; the default build is trust-on-first-use.
- **RGA-070 (S1, fixed):** the subject hands its private `Apply` to the installer-wired
  oracle factory. The wiring is now checked against Root; the negative mismatched-manifest
  path is not exercised by a dedicated suite.
- **P0 set:** all 25 P0 rows are terminal in `spec/audit/closeout.yaml`; external review is
  recommended for the set and required before any value-bearing deployment.

## Evidence index

| Evidence | Path |
|---|---|
| Close-out decisions and evidence | `spec/audit/closeout.yaml` |
| Human-readable summary and residual risks | `docs/src/reference/closeout.md` |
| Findings, including the S1 rows | `spec/audit/findings.yaml` |
| HAZOP rows for manifest and oracle wiring | `spec/hazop/runs/2026-11-07-capabilities/` (CHZ-030, CHZ-032) |
| Capability register | `spec/audit/capabilities.yaml` |
| Live capability and red-team probes | `spec/audit/redteam.yaml`, `spec/audit/redteam-capabilities.yaml` |
| Lean model and axiom audit | `spec/lean/RGen/`, `spec/lean/RGen/Audit.lean` |
| Proof-rigor status and divergences | `spec/proofs/rigor.yaml` |
| Install and manifest code | `harness/install.py`, `crates/rgen-core/src/manifest.rs`, `web/src/lib/store.ts` |
| Oracle wiring code | `contracts/src/lib/KAsset.rho`, `contracts/src/deploy/22_value.rho` |

## S1 trace 1 — manifest substitution (RGA-051)

**Claim under review:** a client can distinguish the genuine Root from a substituted
manifest.

What is implemented:

- `Manifest::from_json_pinned` refuses a manifest whose `root_uri` differs from a pinned
  Root (`crates/rgen-core/src/manifest.rs`), with a unit test.
- The web store refuses a fetched, cached or pasted manifest whose Root differs from
  `VITE_RGEN_ROOT_URI` (`web/src/lib/manifest.ts`), and a non-devnet build without a pin
  fails closed.
- The default build leaves the pin unset, so the trust decision is still
  trust-on-first-use. That is the accepted residual.

Reviewer questions:

1. Is opt-in pinning sufficient for a reference client, or should the default build fail
   closed for every non-devnet profile?
2. Does the pin cover the component map, or only the Root? (It covers the Root; component
   URIs are resolved through Root.)
3. What key distribution and rotation model would make a signed manifest acceptable?

## S1 trace 2 — oracle-factory wiring (RGA-070)

**Claim under review:** the private `Apply` is sent only to the oracle factory the Root
registry names.

What is implemented:

- `makeKAsset` resolves `component:oracle-factory` from Root and refuses to create the
  K-Asset when the installer-wired URI differs (`contracts/src/lib/KAsset.rho`).
- The value-proposition factory is published only when the wired oracle URI matches Root
  (`contracts/src/deploy/22_value.rho`).
- The oracle `openBound` path consumes a one-shot subject snapshot; the raw public
  `open` is gone.

Residual: the mismatched-manifest refusal is a deploy-time path and is not exercised by a
dedicated suite.

Reviewer questions:

1. Is the Root-resolve check at K-Asset creation the right trust anchor, or should the
   factory also return a capability the subject binds to the expected URI?
2. Is the VP publish-time check sufficient, given that a malicious installer can register
   a counterfeit factory in Root?
3. What negative test would the reviewer accept as evidence for the mismatch path?

## Reproduction

The reviewer can reproduce the static and behavioural evidence on an isolated devnet:

```sh
make setup
make spec-check
make lean-check
make unit-all
make redteam redteam-capabilities
make probe-deploy-semantics
make client-test
make web-test web-typecheck
```

The nightly soak runs on its own schedule. The devnet carries no value and the contracts
remain devnet-only.

## Outcome record

Record the reviewer, date, findings, and disposition here when the review is complete.
Until then, the close-out remains owner-authorized and the S1 acceptances remain in force
only until their expiry or the next review, whichever is first.
