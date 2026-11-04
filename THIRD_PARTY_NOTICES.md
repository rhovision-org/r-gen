# Third-party notices

RGen is AGPL-3.0-only. It depends on and composes with:

- **rholo** (RNodeRust), AGPL-3.0 — the node, Rholang runtime, native ERTP, registry and
  REV. Pinned at `841cb842876369deaa63e3b3e26c20d60e6c74c6` for `rchain-crypto`; the node
  parser image used for verification is `e2d073dcd02f1e560ccb84749937138a1e184b0b`.
- **r-cash** (Rholphin), AGPL-3.0-only — accounts, asset resolver, clock and the
  settlement rail. Pinned at `49b441dea4f5561992387ed670ab263fcd5dd164`.
- The Rust crates listed in `Cargo.lock`; their licenses are recorded by `cargo deny`
  where the toolchain is available.
- The seven Dan Robles papers in this directory remain the property of their authors and
  publishers. They are source material, not part of the software license.

No source from r-cash or rholo is vendored into this repository. The contracts are
original Rholang written against their published interfaces.
