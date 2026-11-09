# Quantity, quality and variance

This page defines the value-proposition description used by r-gen and consumed by r-sure.
It is the schema behind `spec/schemas/vp-variance.json`.

## Paper basis

The 2020 Innovation Bank paper makes both branches necessary for value: "The value of an
asset can only be determined if both the quantity and quality are known. An 8-ounce glass
of drinking water is a completely different asset than 8-acre-feet of irrigation water"
(p.5), and "the claim serves as the quantity (definition) and the validation serves as the
quality (characteristics)" (p.5). The paper defines risk as `S × P × E` (p.3). The Bridge
paper equates increased risk with "variance in expectations" (p.3), and the NAIC paper
contrasts "increasing variance of expectations rather than reducing variance" (p.7).

The papers do **not** define a statistical mean/variance schema. The explicit
quantity/quality/variance formulation, including the physical examples (water, screws, a
pipe, a container, a vessel), is Dan Robles's specification and is recorded here as a user
decision, not as a paper sentence.

## Schema

A value proposition declares:

```json
{
  "quantity": {"unit": "m3", "mean": 100},
  "quality": {
    "kind": "water",
    "spec": "potable",
    "scale": {"min": 4, "max": 20},
    "mean": 18
  },
  "variance": {"quantityBps": 400, "qualityBps": 1200, "n": 30}
}
```

- **quantity** is a physical amount with a unit. `mean` is the expected amount.
- **quality** is what the thing is: `kind` and `spec`. The numeric `mean` uses the same
  4..20 scale as the K-Asset's four quality dimensions
  (completeness, correctness, traceability, fitness), so the existing validation rubric is
  reused rather than duplicated.
- **variance** is the dimensionless variance rate for each branch:
  `quantityBps = floor(10000 × Var(quantity) / mean(quantity)²)` and
  `qualityBps = floor(10000 × Var(quality) / mean(quality)²)`. `n` is the sample size.
  The raw second moment is derived, never stored as a float; the core is integer-only.
  The combined rate is `quantityBps + qualityBps`, capped at 10000. This sum is an
  engineering choice: the paper says both branches contribute to value, not that their
  rates add.

### Declared curve

The variance map may also carry the whole distribution as a `risk-curve/v1`:

```json
"variance": {
  "quantityBps": 400, "qualityBps": 1200, "n": 30,
  "curve": {
    "kind": "quantiles",
    "unit": "bpsOfDeclaredValue",
    "n": 16,
    "points": [0, 500, 1000, 1500, 2000, 2500, 3000, 3500,
               4000, 4500, 5000, 5500, 6000, 6500, 7000, 7500]
  }
}
```

The 16 points are equiprobable positions in bps of the declared value, nondecreasing and
each `0..10000`; the sum must be positive. The scalar branch rates remain required as the
summary and the fallback. The curve is snapshotted with the map, so a K-Asset and a claim
carry it unchanged. r-sure reads the curve, computes its stats, and compares it with the
actuary's loss curve; the scalar rate is the legacy projection.

## Flow into the K-Asset

A claim or value proposition reference is checked at claim creation. The VP's variance map
is snapshotted onto the claim and copied to the K-Asset at validation. The K-Asset keeps its
realized `quantity` (the claim) and `quality` (the validation), plus `valuePropositionRef`;
the snapshot is the declared rate map:

```json
"variance": {"quantityBps": 400, "qualityBps": 1200, "n": 30}
```

The snapshot is descriptive. It does not price, score or transfer risk.

## r-sure mapping

r-sure's `variance-is-risk` model defines `varianceRate = σ² / μ²` and
`varianceBps = floor(rate × 10000)`. Its `RgenAdapter` reads the K-Asset. If the variance
snapshot is present, it uses the declared `quantityBps`/`qualityBps` as the engineering
estimate; if the snapshot is absent (old K-Assets), it keeps the existing
quality-rubric-derived `engineeringBps` as the fallback. The insurer estimate, gap, flag,
tolerance and loaded premium are unchanged.

No `risk` token is added to the r-gen core; `tools/check_core_boundary.py` remains green.
