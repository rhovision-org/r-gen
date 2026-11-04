# Citations

Citation keys live in `docs/papers/manifest.json`. Convention: `p.N` is **PDF page N**
(1-based), not the printed page.

| Key | Short name |
|---|---|
| `@robles2020innovation` | The Innovation Bank (IMECE2020-23015) |
| `@zhong2019bridge` | A New Perspective of Accelerated Bridge Construction (IBC 19-10) |
| `@mathews2017bim` | BIM+Blockchain: A Solution to the Trust Problem in Collaboration? |
| `@robles2016naic` | Insurance: The Highest and Best Use Case for Blockchain Technology |
| `@robles2016nspe` | Blockchain Technology: Implications and Opportunities For Professional Engineers |
| `@robles2017stewardship` | The Revolutionary Blockchain – An Opportunity for Engineering Stewardship |

The core contract headers use the form:

```rholang
// Why: ...
// Paper: @key p.N; @key2 p.N
// r-gen decision: ...
```

`@caase2018agenda` is included but uncited; do not cite it. A term with
no paper basis uses `// Paper: none (engineering infrastructure)`.

`tools/check_citations.py` verifies:

1. Every `@key` in a `// Paper:` header exists in the manifest.
2. Every `p.N` is within the paper's page count.
3. Every cited key has `docs/papers/extract/<key>.md` with a `## p.N` heading.
4. Every core deploy term has `// Why:` and `// Paper:` lines.
5. `@caase2018agenda` is never cited.
