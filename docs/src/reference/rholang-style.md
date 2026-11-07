# Rholang control-flow style

> **Scope:** every contract under `contracts/src/`
> **Inventory:** `spec/audit/rholang-control-flow.yaml`
> **Gate:** `make style-check`

The contracts use one linear cell per entity and a consume/re-post discipline. Control flow is
therefore part of correctness: a branch that fails without re-posting the consumed cell loses
state, and a branch that returns early without a reply strands the caller. This page is the
style standard for `if` and `match`, and the reason the gate exists.

## Measured semantics

Verified against the pinned node (`e2d073d`) in `RNodeRust`:

- **No match is silent success.** `resolve_match` returns `None`; the enclosing `Par` simply
  has no effect. The continuation is never fired. This is not an error and not a block. In a
  mutating arm it means the consumed cell is not re-posted and the caller waits forever.
- **First match wins.** Cases are tried in written order; the scrutinee is evaluated once.
- **Tuples** are exact-length and positional. **Lists** are exact-length unless `...rest`,
  which binds the positional suffix only. **Maps/sets** are exact cardinality unless `..._` /
  `...rest`; a named key must be present; a non-collection target does not match a collection
  pattern.
- **Bindings:** bare `x` is a value/process binder, `*x` is a name binder. `@x` is a parse
  error in a match pattern.
- **No guards.** `pattern if cond =>` is not grammar. Use `pattern => if cond then ...`.
- `if`/`else` desugars to a two-case `match` over `true`/`false`; `match` is a flat 12-phlo
  term plus evaluation, so a multi-way `match` is not more expensive than re-evaluating an
  `if` chain.
- A duplicate binder in one pattern is a normalize-time error, not a no-match.

## Rules

1. **`match` for multi-way dispatch.** Status, shape, verdict, outcome, or a tuple of booleans
   with three or more outcomes is a `match`. A single boolean with two outcomes is an `if`.
2. **Exhaustive mutating matches.** Every `match` in an arm that consumes a linear cell ends
   with `_ => { cell!(state) | ret!((false, reason)) }`. The reason is the existing string.
   No silent no-match.
3. **Flatten only total tuples.** `match (status, callerOk, deadlineOk)` is good when every
   component is total. Keep an optional/Nil-sensitive comparison nested under a `match` on
   the optional value: `now > Nil` is an evaluation error, and a tuple match evaluates every
   component before dispatching.
4. **Map patterns are subset patterns.** Use `{"uri": uri, ..._}` or
   `{"hash": h, ..._}` for a state map that may carry extra fields. Without `..._` the pattern
   requires an exact key set. Missing key, non-map or `Nil` falls to `_`. Dynamic keys
   (`state.get(var)`) cannot be patterns.
5. **Bind correctly.** `x` for a value, `*x` for a contract or capability; never `@x` in a
   pattern.
6. **One table per mapping.** A verdict maps to `(claimStatus, kassetStatus)` in one
   `match`; an outcome maps to a target status in one `match`. Do not copy the table into a
   second contract.
7. **No branch-only channel round-trips.** Do not spawn a channel and a `for` to compute a
   small default or a one/two-element list. Inline a `match` or return a tuple. A helper is
   fine when it is reused and is already match-shaped (`patchOr`, `minLevelOf`).
8. **Preserve order and strings.** First-match order, refusal reason, reply arity and the
   exact re-post are the interface. Tests assert them.

## Gate

`tools/check_rholang_style.py` is a heuristic brace/token scanner, not a parser. It hard-fails
on:

- a `match` in a mutating arm with no catch-all (`_`, a lone binder, or a total tuple bind);
- `@` inside a match pattern;
- a map pattern without `..._` when the match target is a `.get(...)` or state map.

It warns on deep match nesting, `else if` chains, duplicate verdict/outcome tables, and files
with many `if`s and no `match`. The behavioral suites and the red team remain the gate; a clean
scanner is not a proof.

```bash
make audit-control-flow   # regenerate spec/audit/rholang-control-flow.yaml
make style-check          # enforce the hard rules, print warnings
```

## Audit result (2026-11-07)

The heuristic inventory moved from 107 `if` / 92 `match` to 88 `if` / 99 `match` after the
refactor. The guard staircases were flattened in `Scope.scopeMatches`, `Issuer.authorize`,
`Credential.check`/`prove`, `GenRoot.register`, `IdentityFactory.resume` and `Claim.comment`.
The verdict table is now one `match` in `finalizeValidation`; the outcome table is one helper in
`contracts/src/lib/Status.rho`; provenance `create`/`anchor` use subset map patterns; the oracle
`decide`/`execute` arms have explicit adjudicator/execution builders.

The style gate now reports no hard failures. The remaining 14 warnings are match-nesting depth
5–8, mostly inside `KAsset.nest`/`nestProofs` and `verifyChildClaim`. Those are deferred
state-shape/API refactors: collapsing the four `List.rho` recursors, a map-keyed anchor store,
and merging `approve`/`reject` and `prove`/`proveValidated`. They are recorded in the inventory,
not silently waived.

## Reviewer checklist

- Does every mutating `match` have an explicit `_` that re-posts and replies?
- Is every tuple in a match total (no `Nil` comparison, no missing optional)?
- Does every map pattern use `..._` when the map may have extra keys?
- Is the first-match order the same as the old `if` order?
- Is the refusal string and reply arity unchanged?
- Is the status/outcome table defined once?
