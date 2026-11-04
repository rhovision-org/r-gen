# Rholang improvement plan

This is the ranked Rholang backlog from the audit and HAZOP. The machine-readable record is
[`spec/improvements/rholang.yaml`](https://github.com/rhovision-org/r-gen/blob/main/spec/improvements/rholang.yaml).
Every item cites a finding and at least one HAZOP row; Phase 2 may not start until the review accepts
the finding.

## Staged policy

Phase 1 changes no contract. Phase 2 implements accepted items with the listed tests and a
compatibility note. A breaking change requires a migration note and an updated suite. A P0 is not
“fix immediately”; it is “requires an explicit review decision before Phase 2”. The review may
accept, reject, or accept the risk.

## Ranked items

| ID | Priority | Finding | Change | Compatibility |
|---|---|---|---|---|
| RR-01 | P1 | RGA-023 | Bind oracle open to the subject and verify parties; keep decide/execute bound to the stored adjudicator and private Apply | Breaking for unauthenticated openers |
| RR-02 | P1 | RGA-022 | Authenticate and bind provenance creation; reject empty writers | Breaking for anonymous creation and empty writer lists |
| RR-03 | P1 | RGA-021 | Bind validated proofs to `nowHeight`, or verify the supplied height; keep the caller field | Breaking for future/historical proof heights |
| RR-04 | P1 | RGA-020 | Make Claim and K-Asset verdict mappings total and aligned; reject unknown verdicts before any write | Breaking for unknown verdicts |
| RR-05 | P1 | RGA-025 | Cap `KAsset.nest` count, depth, and per-child work; record the cost | Breaking only for oversized batches |
| RR-06 | P2 | RGA-027 | Rename/document `Credential.check` as advisory, or authenticate the caller | Additive if authenticated; breaking for caller-nominated checks |
| RR-07 | P1 | RGA-026 | Validate deadlines, comment-window ordering, quantities, and parties at creation | Breaking for impossible/expired schedules |
| RR-08 | P1 | RGA-024 | Make oracle execution retry-safe with an application receipt; keep the crank outcome-blind | Additive receipt; migration for old in-flight cases |
| RR-09 | P2 | RGA-028 | Decide and document whether identity is required for claim/comment participation | Breaking only if enforcement is chosen |
| RR-10 | P2 | RGA-029 | Cap or measure registry growth and create serialization | No normal-size change; cap is breaking at the cap |
| RR-11 | P1 | RGA-031 | Make identity create, claim mint, and nest proof consumption recovery-safe | Additive records; migration if in-flight records exist |

The HAZOP rows for each item are in the manifest. Representative links:

- RR-01: `HZ-ORACLE-004`, `HZ-ORACLE-005`.
- RR-02: `HZ-PROV-002`, `HZ-PROV-003`, `HZ-PROV-012`.
- RR-03: `HZ-VP-005`, `HZ-VP-013`.
- RR-04: `HZ-CLAIM-004`, `HZ-CLAIM-005`, `HZ-CLAIM-007`.
- RR-05: `HZ-DEPLOY-002`, `HZ-KASSET-016`.
- RR-07: `HZ-CLAIM-016`, `HZ-VP-016`, `HZ-ORACLE-016`.
- RR-08: `HZ-ORACLE-013`, `HZ-ORACLE-015`.
- RR-11: `HZ-ID-011`, `HZ-CRED-015`, `HZ-CLAIM-015`, `HZ-KASSET-015`.

## Phase 2 progress

- RR-04 is fixed: `claimStatus` and `kassetStatus` both map `valid` to validated, `partial` to
  conditional/validated, and `invalid` or unknown to rejected. An unknown verdict no longer produces
  a validated claim beside a rejected K-Asset. Pre-write rejection remains a follow-up.
- RR-01 is partial: `OracleFactory.open` now authenticates the opener and requires it to match
  `caseReq.openedBy`. Parties and `subjectRef` remain caller-supplied; registry binding is open.
- RR-02 is partial: `ProvenanceFactory.create` now authenticates the creator and rejects an empty
  writer list. `assetRef` is still a free string; asset-registry binding is an extension.
- RR-08 is partial: `Apply.applyDecision` returns `already applied` when the K-Asset already has the
  decision outcome, so an oracle retry can record success after a partial cross-contract failure. An
  explicit execution receipt is still open.
- RR-03 is fixed: `ValueProposition.proveValidated` reads `nowHeight` and rejects a supplied
  `atHeight` that differs from chain height.
- RR-05 is fixed: `KAsset.nest` caps a batch at 32 children and the parent list at 64, rejecting
  larger batches before proof consumption.
- RR-07 is partial: claim creation now requires a deadline and rejects a comment window after the
  deadline. Claim and VP creation now require a future deadline; oracle future-ness remains open.
- The other items remain proposed. The devnet suites were not re-run after the contract changes in
  this environment because the isolated node failed to start (exit 137); `parse-check` passes and
  the changes are static. Re-run `make install unit-all` before promotion.

## Policy decisions

- RR-06: `Credential.check` is advisory. It accepts a caller-nominated subject and no core commit
  may use it; `tools/check_concurrency.py` forbids it as a commit authority.
- RR-09: identity is not a prerequisite for claim or comment participation. This is documented as
  intentional; `harness/unit_claim.py` already exercises an unregistered commenter. It can be
  revisited if Sybil resistance becomes a requirement.
- RR-10: `directoryState` and `factoryState` remain explicit serialization points. No cap or
  sharding is implemented; a cap would be a breaking change at the cap.

## Atomicity residual risk (RR-11)

The remaining P0 findings are cross-cell failure windows, not guard bypasses:

- **Identity create:** `identityState` and the bundle registration precede the `directoryState`
  write. A failure after registration but before the directory write can leave an identity cell
  and bundle that the directory does not reference; a retry can create a second one. A recovery
  record needs the emitted identity URI and a pending/finalized directory status.
- **Claim validation:** `finalizeValidation` mints the K-Asset before writing the claim's
  `validationRef` and `kassetRef`. A failure between those writes can leave a K-Asset with no
  claim reference, or allow a retry to mint another. A validation receipt in the claim state is
  the intended fix.
- **K-Asset nest:** `nestProofs` consumes each child approval proof before the parent writes
  `childRefs`. A failed parent write consumes the proofs while the parent is unchanged. A nest
  receipt that records the consumed child ids or the proof payloads is the intended fix.

No current Phase 2 change claims to close these. They remain accepted P0 items with the failure
window documented; the devnet suites cannot exercise them without crash/failure injection.

## Why these orderings

- **State integrity first.** RR-04 and RR-11 prevent a claim and its K-Asset, or a parent and its
  child proofs, from disagreeing. They are the highest-value contract changes.
- **Authority next.** RR-01 and RR-02 close unauthenticated record creation. Neither is a direct
  authority bypass today, because the private Apply and the advisory nature of provenance limit the
  impact; both are record-integrity hazards.
- **Time and resources after that.** RR-03, RR-05, and RR-07 remove caller-controlled height,
  unbounded nest work, and impossible schedules. They are availability and API hazards.
- **Documentation and policy last.** RR-06, RR-09, and RR-10 make advisory and design choices
  explicit. They may close with no code change.

## What is not in this plan

No KATs, payments, risk scoring, panels, governance, handles, or metrics primitives. They remain
extensions. No change to the five paper-derived primitives' core purpose. No new token or minting
arm. No attempt to make the contracts a refined implementation of the Lean model; that requires a
Rholang semantics, which this repository does not have.

## Test plan

Each item names the harness suite that must gain a negative case before the fix and a passing case
after it:

| Item | Suite |
|---|---|
| RR-01 | `harness/unit_oracle.py` |
| RR-02 | `harness/unit_provenance.py` |
| RR-03 | `harness/unit_value.py`, `harness/unit_kasset.py` |
| RR-04 | `harness/unit_claim.py`, `harness/integration_core.py` |
| RR-05 | `harness/unit_kasset.py` |
| RR-06 | `harness/unit_credentials.py` |
| RR-07 | `harness/unit_claim.py`, `harness/unit_value.py`, `harness/unit_oracle.py` |
| RR-08 | `harness/unit_oracle.py`, `harness/concurrency_core.py` |
| RR-09 | `harness/unit_claim.py` |
| RR-10 | `harness/unit_identity.py`, `harness/unit_credentials.py` |
| RR-11 | `harness/unit_identity.py`, `harness/unit_claim.py`, `harness/unit_kasset.py`, `harness/concurrency_core.py` |

The devnet suites are nightly/manual (RGA-011). A Phase 2 change that cannot be covered statically
adds its negative test to the nightly job and documents that it did not run on the pull request.

## Open decisions for the review

1. Keep `proved-conformance` and define it as an evidence bundle, or rename it
   `model-vector-conformance`? Recommendation: keep the name, publish the definition.
2. Oracle execution: keep a permissionless crank with an idempotent receipt, or require subject
   authorization? Recommendation: keep the crank, make it outcome-blind and receipt-backed.
3. Identity participation: enforce an Identity record, or document permissionless participation as
   intentional? Recommendation: document it, test it, and revisit if Sybil resistance is a goal.
4. Provenance creation: require an asset registry binding, or state that provenance is advisory?
   Recommendation: require a creator capability and non-empty writers now; treat registry binding as
   an extension.
