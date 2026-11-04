# RGen paper archive

The papers are source material for the primitives, not part of the software license.

> **NOTICE.** These are third-party copyrighted works. They are **not** covered by RGen's
> AGPL-3.0-only license and are **not** part of the software distribution. They are kept
> here as cited reference material. Redistribution status differs per paper; see the
> manifest. For a public release, replace non-redistributable PDFs with links and keep only
> the short page-cited extracts.

## Index

| Key | Paper | Authors | Venue | Pages |
|---|---|---|---|---|
| `@robles2020innovation` | The Innovation Bank | Daniel R. Robles, Bradley E. Layton | ASME IMECE 2020 | 9 |
| `@zhong2019bridge` | A New Perspective of Accelerated Bridge Construction | Joan Zhong-Brisbois, Daniel Robles | IBC 19-10 | 7 |
| `@mathews2017bim` | BIM+Blockchain: A Solution to the Trust Problem in Collaboration? | Malachy Mathews, Dan Robles, Brian Bowe | CITA BIM Gathering 2017 | 11 |
| `@robles2016naic` | Insurance: The Highest and Best Use Case for Blockchain Technology | Daniel R. Robles | NAIC CIPR, July 2016 | 11 |
| `@robles2016nspe` | Blockchain Technology: Implications and Opportunities For Professional Engineers | Daniel R. Robles (for NSPE) | NSPE FinTech Task Force, 2016 | 40 |
| `@robles2017stewardship` | The Revolutionary Blockchain – An Opportunity for Engineering Stewardship | Daniel R. Robles, Matthew E. Bowers | ASCE Grand Challenge 2017 | 6 |

`@caase2018agenda` is a conference program, uncited, and quarantined under `uncited/`.

## Citation convention

`p.N` means **PDF page N**, 1-based, not the printed page. Every quote used in code or docs
must appear in `extract/<key>.md` under a `## p.N` heading. The manifest records the PDF
SHA-256 so the archive can be checked for drift.

## Per-paper redistribution status

- `mathews2017bim` — CC BY-NC-SA 3.0. Attribution, non-commercial, share-alike.
- `robles2016nspe` — NSPE copyright; limited attribution. Do not redistribute without
  permission.
- `robles2016naic` — NAIC copyright; further distribution prohibited.
- `robles2020innovation` — ASME copyright; all rights reserved.
- `zhong2019bridge`, `robles2017stewardship` — no stated license.
- `caase2018agenda` — conference program; uncited.

`tools/check_paper_licenses.py` fails a `RGEN_PUBLIC_RELEASE=1` build if a
non-redistributable PDF is tracked.

## Extracts

`extract/` contains short, page-cited quotations used to justify the primitives. It does
not contain full text. The citation checker verifies that every key and page cited by the
core contracts has an extract heading.
