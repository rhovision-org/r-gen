# Identity

## Paper anchor

> "Records" (identity/credential context). — `@robles2016nspe p.40`

> "'Claim' and 'Validation' represent a key mechanism i.e. the 'handshake'." — `@zhong2019bridge p.4`

The papers assume identified practitioners and participants. r-gen turns that assumption into
a first-class, per-address identity cell and a first-writer-wins directory.

## What the paper means

The NSPE record/identity passage treats records as attributable to a person or firm; the
Bridge handshake assumes the talent pool and selection criteria identify who may act. The core
does not invent a global reputation system; it records the address that owns an identity and
the address that authored each fact.

## How the Rholang expresses it

- `contracts/src/deploy/10_identity.rho` — `IdentityFactory@"create"` consumes
  `directoryState`, rejects a duplicate address, creates a per-address `Identity` cell, and
  appends the address-to-URI entry.
- `IdentityDirectory@"lookup"` / `"count"` are peeks of `directoryState`; they never write.
- `Identity@"get"` peeks `identityState`; `Identity@"update"` consumes it and requires the
  caller to be the current owner.

## What the Lean proves

- `RGen.Directory.create_unique` — a successful create makes a second create at the same
  address fail.
- `RGen.update_owner_requires_owner` — only the current owner can transfer the identity.
- `RGen.update_owner_preserves_address` — the address is never rewritten.
- `RGen.core_arm_authority` — the create/update decisions factor through their consumed cell.

## Deliberately excluded

Handles, global uniqueness of human-readable names, and reputation scores are extensions.
The core uses the REV address as the identity.

## See also

- [Core arm reference](../reference/arms.md)
- [Paper-to-code matrix](../reference/paper-to-code.md)
- [Pareto ledger](../reference/pareto-ledger.md)
- Suite: `harness/unit_identity.py`
