# Close-out ledger

`spec/audit/closeout.yaml` is the terminal record for every P0/P1 finding. It is checked
by `tools/check_closeout.py` (`make check-closeout`) and included in `make spec-check`.

## Standard

Every P0/P1 finding ends in exactly one decision:

- **fixed** — a code, proof, gate or documentation change with evidence that exists;
- **risk-accepted** — an explicit owner, rationale, expiry and bounded-behaviour
  evidence; the acceptance expires at the next independent review or the recorded date,
  whichever is first;
- **narrowed-claim** — the public wording is corrected to match the theorem or contract.

A row whose decision disagrees with its finding disposition fails the checker. A
`risk-accepted` row without an owner or a future expiry fails it. A P0/P1 finding without
a row fails it. The checker warns when a `fixed` row cites only code; the warning is kept
visible rather than hidden by a blanket doc reference.

## Result

At the 2026-11-08 baseline the ledger has **59 P0/P1 rows**: 25 P0 and 34 P1.

| Decision | Rows |
|---|---|
| fixed | 47 |
| risk-accepted | 12 |
| narrowed-claim | 0 |

The twelve accepted risks are:

| ID | Risk | Why it is accepted | Expiry |
|---|---|---|---|
| RGA-006 | Axiom audit is a hand-maintained list | `--audit-coverage` requires every Pareto theorem in `Audit.lean`; a theorem outside the Pareto vocabulary can still escape | 2027-05-08 |
| RGA-011 | Devnet suites are nightly, not PR-gating | The full suite needs an 8 GB isolated devnet; the nightly run is the evidence tier | 2027-05-08 |
| RGA-029 | Registries grow without a cap | `directoryState` and `factoryState` are documented serialization points; a cap is a breaking change | 2027-05-08 |
| RGA-040 | `proveApproved` is permissionless | The proof is data with no victim state; the caller pays; nesting still requires the parent claimant | 2027-05-08 |
| RGA-051 | Unsigned manifest | Root pinning is implemented and tested; the default build is trust-on-first-use; signing remains future work | 2027-05-08 |
| RGA-052 | Installer is Root writer and genesis Issuer | One genesis key controls both; key loss is the threat model; rotation is a governance extension | 2027-05-08 |
| RGA-053 | Registry insertion is unauthenticated | A URI is a designation, not an endorsement; every consumer must verify factory membership | 2027-05-08 |
| RGA-054 | Oracle/claim clock arms have no caller check | They are cranks, not decisions; `execute` replays only the stored decision through the case-bound Apply | 2027-05-08 |
| RGA-055 | Approval survives approver revocation | The proof is height-bound; de-approval needs a new transition and a liability policy | 2027-05-08 |
| RGA-062 | Validation survives validator revocation | The proof is height-bound; devalidation needs a new transition | 2027-05-08 |
| RGA-063 | Provenance writers cannot be revoked | Provenance is advisory; no core arm uses it as authority; `removeWriter` needs a writer-consent policy | 2027-05-08 |
| RGA-071 | A decided case with a permanently refusing subject Apply cannot close | A terminal abandon needs a liability policy; the execution receipt records the failure | 2027-05-08 |

## Residual risks carried by fixed rows

Several fixed rows carry a documented residual rather than a new finding:

- **RGA-022** — provenance is bound to a subject capability, but a third party can still
  create an advisory record for a public subject.
- **RGA-023** — a forged subject snapshot can create an advisory case; its Apply is the
  forger's own and cannot touch a real subject.
- **RGA-033** — the nest receipt is exercised by an unsorted batch; true mid-deploy crash
  injection remains skipped.
- **RGA-065** — a claim receipt stranded before the mint is not resumable by design;
  recovering it needs a lease/fencing protocol.
- **RGA-070** — the mismatched-manifest refusal is a deploy-time path; it is not exercised
  by a dedicated suite.
- **RGA-051** — the S1 manifest substitution is accepted only because pinning is opt-in.

## Review and independence

The ledger is owner-authorized. There is one maintainer. No independent technical review
has been performed. External review is required before any value-bearing deployment and is
specifically required for the S1 rows (RGA-051, RGA-070) and recommended for the P0 set.
The acceptance dates above are not a substitute for that review.

## Regenerating

The ledger is generated from `spec/audit/findings.yaml` and then edited by hand when a
finding's evidence needs a test or theorem reference. `make check-closeout` is the gate;
`make spec-check` runs it.
