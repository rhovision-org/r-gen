# Rholang model used by the core

The papers define the engineering domain, not Rholang semantics. The concurrency argument
rests on the pinned rholo runtime:

- **Linear channels.** A name with one message is a cell. `for (@s <- state)` removes the
  message; a second consumer blocks until the first re-posts. This is the single-writer
  linear cell used for every entity. Source: `RNodeRust/rholang/src/reduce.rs`, the
  interpreter's receive/send rules, and `RNodeRust/docs/src/formal/`.
- **Peek `<<-`.** A read that leaves the message in place; used by read-only arms
  (`get`, `comments`, `verify`, `authorize`, `covers`).
- **Bundle `bundle+{*Contract}`.** The published capability; only the named contract is in
  the bundle. Private helpers (`Apply`, `KAsset` in the Claim term) are not in the bundle.
- **Deploy atomicity.** A deploy's state changes are rolled back on failure; the core avoids
  relying on `1/0` for a pending flag. Refusals re-post the consumed state and reply
  `(false, reason)`.
- **No names in state.** State maps hold data (`String`, `Int`, `Bool`, `List`, `Map`,
  `Nil`). Capabilities live in process closures. This avoids serialization and equality
  ambiguity for names.
- **Registry URIs.** `rho:registry:insertArbitrary` returns a URI value. The credential
  registry canonicalizes it with `uri.toString()` so a caller's string URI matches the
  stored key.

The core does not use `rho:rchain:makeMint`, ERTP, r-cash, or any extension system process.
The native `rho:block:data` and `rho:crypto:blake2b256Hash` are the only system processes
used for time and hashing.
