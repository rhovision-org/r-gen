# K-Asset conventions v1

> **Version:** `kasset.conventions/v1`
> **Status:** Interface convention. The Pareto core stores these fields but does not enforce
> this document. Consumers must validate the state themselves.

This page defines the K-Asset state shape and status semantics that an interoperating
consumer may rely on. The machine-readable schema is
`spec/schemas/kasset-conventions.json`; the conformance fixture is
`spec/fixtures/kasset-conventions-v1.json`; the vectors are
`spec/vectors/kasset-conventions.tsv`.

The core's authority is the deployed Rholang. If this page and the contracts disagree, the
contracts win and this page is wrong.

## State shape

`KAsset!("get", *ret)` is a read-only peek. It returns `(true, state)`, where `state` includes:

| Field | Shape | Meaning |
|---|---|---|
| `quantity` | `{unit: non-empty string, value: integer >= 1}` | What the claim counts, and how many. |
| `quality` | `{completeness, correctness, traceability, fitness}`, each integer 1..5, sum 4..20 | The validation's quality record. |
| `verdict` | `valid`, `partial`, or `invalid` | The validator's judgement. |
| `status` | See the lifecycle below. | The K-Asset's current state. |
| `approval` | Absent before approval (the node drops `Nil` map values); otherwise `{decision, liability, ...}` | The approval record. |
| `approval.liability` | `{responsible: string, shareBps: integer 0..10000, basisHash?: string}` | Who accepted liability and in what share. |

`quantity`, `quality`, and `liability` are stored as supplied. The current core does not
validate their shapes. A consumer that depends on them must check them.

## Quality rubric

The four-dimension rubric is the convention for this version:

- `completeness`
- `correctness`
- `traceability`
- `fitness`

Each is an integer from 1 to 5; the sum is 4 to 20. The key names and ranges are stable for
`kasset.conventions/v1`. Changing them requires a new version.

If a dimension is missing, duplicated, non-integer, or outside 1..5, refuse automatic
derivation and require a bound attestation. The harness uses this rubric; the legacy
`KAssetBook` validates it, but the Pareto core does not.

## Status lifecycle

| Status | How it arises | Approval and liability | Automatic derivation |
|---|---|---|---|
| `validated` | A `valid` verdict at mint. | None. | No; require an attestation. |
| `conditional` | A `partial` verdict at mint. | None. | No; require an attestation. |
| `rejected` | An `invalid` verdict at mint, or a rejection. | None. | No. |
| `approved` | Approval from `validated` or `conditional`. | Present. | Yes. |
| `disputed` | A party opens a dispute on an approved asset. | Retained, but the asset is under dispute. | No; require an attestation. |
| `upheld` | An oracle decision upholds the approval. | Retained. | No; require an attestation. |
| `revoked` | An oracle decision revokes the approval. | Retained as history. | No. |
| `partially_revoked` | An oracle decision partially revokes it. | Retained as history. | No; require an attestation. |

`approved` is the only status eligible for automatic derivation. An `upheld` asset keeps its
approval and liability, but `KAsset!("proveApproved")` only matches `approved`; treat it as
attestation-only. `revoked` and `rejected` are never derivable.

## Liability share

`approval.liability.shareBps` is the approver's declared share of liability, from 0 to 10000.
It is not a measure of engineering variance. A lower share is a different allocation of
indemnity or co-insurance, not evidence that the engineering work is worse.

Do not add a liability-share penalty to the engineering variance rate. If an insurer wants
to price retained risk, record it as a separate underwriting or co-insurance parameter, not
as part of the engineering estimate.

## Engineering variance

For an approved K-Asset with a valid or partial verdict and a complete quality rubric:

```
qualitySum      = completeness + correctness + traceability + fitness
D               = 20 - qualitySum
verdictPenalty  = 0 for valid, 1000 for partial
engineeringBps  = D * 500 + verdictPenalty
```

The range is 0..9000 for eligible assets. The liability share is not an input.

The conformance fixture `spec/fixtures/kasset-conventions-v1.json` pins:

- `quality` all 3, so `qualitySum = 12` and `D = 8`;
- `verdict = valid`, so `verdictPenalty = 0`;
- `status = approved`, with `shareBps = 10000`;
- `engineeringBps = 4000`.

The harness test in `harness/unit_kasset.py` creates, validates and approves that asset and
asserts the returned state and the rate. If the state shape changes, that test fails first.

## Attestation fallback

When the state is not eligible, or a dimension is missing, a consumer may use a bound
attestation instead of deriving:

```json
{
  "source": "attested",
  "kassetUri": "rho:id:...",
  "varianceBps": 4000,
  "evidenceHash": "..."
}
```

Bind it to an evidence entry `{kind: "rgen:kasset", uri, hash}`. Record the source and the
gap against any insurer estimate. An attestation is an explicit override, not a silent
substitute for the convention.

## Versioning

`kasset.conventions/v1` is the current version. Additive fields do not require a version
bump. Changes to field names, quality dimensions, ranges, status meanings, or eligibility
require `kasset.conventions/v2`. The schema and this page carry the version identifier; the
core does not.
