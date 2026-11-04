# Third-party notices

RGen is AGPL-3.0-only. The Pareto core has no r-cash or ERTP dependency.

- **rholo** (RNodeRust), AGPL-3.0 — the node, Rholang runtime, registry, and native system
  channels. The Rust client pins `rchain-crypto` at
  `841cb842876369deaa63e3b3e26c20d60e6c74c6`. The verification node is
  `e2d073dcd02f1e560ccb84749937138a1e184b0b`.
- Rust crates in `Cargo.lock`; their licences are recorded by the crates themselves.
- The papers under `docs/papers/` are **third-party copyrighted works, not AGPL** and not
  part of the software distribution. Per-paper authors, venues, SHA-256 and redistribution
  status are in `docs/papers/manifest.json`.

| Paper | Authors | Venue | Status |
|---|---|---|---|
| The Innovation Bank | Daniel R. Robles, Bradley E. Layton | ASME IMECE 2020 | ASME copyright; no redistribution |
| A New Perspective of Accelerated Bridge Construction | Joan Zhong-Brisbois, Daniel Robles | IBC 19-10 | no stated licence |
| BIM+Blockchain | Malachy Mathews, Dan Robles, Brian Bowe | CITA BIM Gathering 2017 | CC BY-NC-SA 3.0 |
| Insurance: The Highest and Best Use Case for Blockchain Technology | Daniel R. Robles | NAIC CIPR, July 2016 | NAIC copyright; further distribution prohibited |
| Blockchain Technology: Implications and Opportunities For Professional Engineers | Daniel R. Robles (for NSPE) | NSPE FinTech Task Force, 2016 | NSPE limited/attribution |
| The Revolutionary Blockchain | Daniel R. Robles, Matthew E. Bowers | ASCE Grand Challenge 2017 | no stated licence |
| CAASE18 Final Agenda | NAFEMS | CAASE18 | quarantined, uncited |

For a public release, replace non-redistributable PDFs with links and keep only the short
page-cited extracts. `RGEN_PUBLIC_RELEASE=1 tools/check_paper_licenses.py` fails if a
non-redistributable PDF is tracked.
