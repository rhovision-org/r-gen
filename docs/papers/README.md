# r-gen paper archive

The papers are source material for the primitives and are included as cited reference
material. They are already public on Arweave and the authors' websites.

> **NOTICE.** These are third-party copyrighted works. They are **not** covered by r-gen's
> AGPL-3.0-only license. The PDFs are included as reference material; the copyrights remain
> with their holders. See `manifest.json` for authors, venues, pages and SHA-256.

## Index

| Key | Paper | Authors | Venue | Pages |
|---|---|---|---|---|
| `@robles2020innovation` | The Innovation Bank | Daniel R. Robles, Bradley E. Layton | ASME IMECE 2020 | 9 |
| `@zhong2019bridge` | A New Perspective of Accelerated Bridge Construction | Joan Zhong-Brisbois, Daniel Robles | IBC 19-10 | 7 |
| `@mathews2017bim` | BIM+Blockchain: A Solution to the Trust Problem in Collaboration? | Malachy Mathews, Dan Robles, Brian Bowe | CITA BIM Gathering 2017 | 11 |
| `@robles2016naic` | Insurance: The Highest and Best Use Case for Blockchain Technology | Daniel R. Robles | NAIC CIPR, July 2016 | 11 |
| `@robles2016nspe` | Blockchain Technology: Implications and Opportunities For Professional Engineers | Daniel R. Robles (for NSPE) | NSPE FinTech Task Force, 2016 | 40 |
| `@robles2017stewardship` | The Revolutionary Blockchain – An Opportunity for Engineering Stewardship | Daniel R. Robles, Matthew E. Bowers | ASCE Grand Challenge 2017 | 6 |
| `@caase2018agenda` | CAASE18 Final Agenda with Initial Abstracts | NAFEMS | CAASE18, 2018 | 241 |

All seven PDFs are under `pdf/`. `@caase2018agenda` is included but uncited; it is not used
as a source for a core primitive.

## Citation convention

`p.N` means **PDF page N**, 1-based, not the printed page. Every quote used in code or docs
must appear in `extract/<key>.md` under a `## p.N` heading. The manifest records the PDF
SHA-256 so the archive can be checked for drift.

## Extracts

`extract/` contains short, page-cited quotations used to justify the primitives. It does
not contain full text. The citation checker verifies that every key and page cited by the
core contracts has an extract heading.
