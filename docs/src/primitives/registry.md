# Creation registries

The core has append-only creation registries for credentials (`factoryState`), claims
(`claimRegistryState`), value propositions (`vpRegistryState`), and identities
(`directoryState`). They are engineering infrastructure, not a paper primitive.

## What they do

- Serialize creation so a forged URI cannot be resolved as genuine.
- Make `verify(uri)` monotone: once true, it stays true.
- Keep the hot path per-entity; validation, approval, decision, nesting, and provenance do not
  write a registry.

## How the Rholang expresses it

- `CredentialFactory@"issue"` writes `factoryState`; `@"verify"` peeks it.
- `ClaimFactory@"create"` writes `claimRegistryState`; `@"verify"` peeks it.
- `ValuePropositionFactory@"propose"` writes `vpRegistryState`; `@"verify"` peeks it.
- `IdentityFactory@"create"` writes `directoryState`; `IdentityDirectory@"lookup"` peeks it.

## What the Lean proves

- `RGen.Registry.verify_monotone` — registration never un-verifies an entry.
- `RGen.Registry.register_twice` / `register_unique` — a duplicate registration is refused.
- `RGen.Directory.create_unique` — first-writer-wins identity creation.
- `RGen.core_arm_authority` — the create/issue decisions factor through their consumed cells.

## Deliberately excluded

There is no global nonce, no admin registry, and no off-chain indexer. Registries are
creation-only serialization points.

## See also

- [Core arm reference](../reference/arms.md)
- [Formal model](../reference/formal-model.md)
