# Verification record

**Date:** 2026-11-04
**Node:** rholo `e2d073dcd02f1e560ccb84749937138a1e184b0b`
**Devnet:** isolated `rgen-bootstrap` on 40403/40405/40402 (8 GB), existing networks untouched
**Core:** 7 deploy terms, 16 catalogue components, 10 state cells

## Passed

- `tools/build_contracts.py --check`: 7 terms, no drift.
- `tools/parse_check.sh` on all rendered core terms: 7/7 OK.
- `tools/check_arch.py`: 16 components, 10 state cells, acyclic.
- `tools/check_captures.py`, `check_placeholders.py`, `check_money.py`: pass.
- `harness/unit_core.py`: pass — identity → credential → value proposition → claim →
  validation → K-Asset → approval → dispute → oracle → provenance.
- `harness/concurrency_core.py`: pass — one of two validations wins; one of two approvals
  wins; exactly one oracle apply; cross-subject isolation; two comments both stored; eight
  independent claims validate in one deploy; a revoked credential refuses.

## Baseline

The pre-Pareto 12-term prototype is on tag `legacy-2026-11-04`; its 12/12 suite result is
the baseline, not the target. The core does not install KAT, payments, risk, panels,
admin, handles, or metrics; those are extensions.

## Reproduce

```sh
make venv
make build-check parse-check
make check-core-boundary check-concurrency check-citations
make install
make unit-core
make concurrency
```

**Honest limit:** the core has two behavioural suites (vertical slice and race suite). The
extension suites (receipt, payments, risk, panels) are not implemented in this tree.
