# Provenance

## Paper anchors

> "The asset becomes the keeper of its own information." — `@robles2016nspe p.29`

> "their provenance and ownership" — `@zhong2019bridge p.3`

> "Tokens issuance marks points where risk is transferred from one party to another."
> — `@zhong2019bridge p.6`

## What the paper means

Provenance belongs to the asset, not to a global book. Documents and comments are anchored
to the asset; a parent hash gives the minimal document graph. The core records anchors and
comments; token issuance and risk transfer are extensions.

## How the Rholang expresses it

- `contracts/src/deploy/40_provenance.rho` — `ProvenanceFactory@"create"` creates a
  per-asset cell with an `assetRef` and a writer list.
- `Provenance@"anchor"` requires a writer, a non-empty hash, and a non-duplicate anchor;
  it appends `{id, kind, hash, parentHash, by, at}`.
- `Provenance@"comment"` requires a writer and appends a comment.
- `Provenance@"verify"` is a monotone read of the anchor list.

## What the Lean proves

- `RGen.P1_anchors_append_only` — anchors are append-only.
- `RGen.ProvenanceState.anchor_unique`, `verify_monotone`,
  `addComment_requires_writer`, `addAnchor_nonempty_hash`.
- Pair matrix: `provenance_anchor_anchor_same_never_after`,
  `provenance_comment_comment_appends`.

## Deliberately excluded

Global provenance registries, IPFS pinning policy, and risk-transfer/token issuance are
extensions. The core anchors hashes and comments to the asset.

## See also

- [Paper-to-code matrix](../reference/paper-to-code.md)
- Suite: `harness/unit_provenance.py`
