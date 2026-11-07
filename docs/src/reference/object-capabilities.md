# Object capabilities

RGen's authority is name-based. A Rholang name is unforgeable; sending the name delegates the
ability to use it; `bundle+{*Contract}` publishes only the invocation surface of one contract.
This page records how the core uses that primitive, which matches are capability checks and
which are only data checks, and the hazards that remain.

The machine-readable register is
[`spec/audit/capabilities.yaml`](https://github.com/rhovision-org/r-gen/blob/main/spec/audit/capabilities.yaml);
the gate is `tools/check_capabilities.py`. The live probes are
`harness/redteam_capabilities.py`; the blind run is in
`spec/hazop/runs/2026-11-07-capabilities/`.

## The model

- **Designation is not authority.** A registry URI designates a term; it does not endorse it.
  Anyone can insert an arbitrary term and receive a fresh URI. The installer-gated Root and
  the factory issuance registries are the two anchors that turn a URI into an entity a core
  consumer will accept.
- **`bundle+` is the published form.** A contract is invoked by sending on its name, so `+`
  (send-capable) is the useful attenuation. `bundle-` would allow receiving on the name, not
  invoking the contract; `bundle0` would be inert. The core uses only `bundle+`.
- **A bundle cannot be projected.** `bundle+{*KAsset}` exposes every arm of the K-Asset:
  `get`, `approve`, `reject`, `proveApproved`, `nest`, `openDispute`, `children`,
  `revocation`. There is no read-only bundle for a contract whose reads are also sends, and no
  time-bound grant. Safety therefore rests on a check inside every mutating arm, not on the
  shape of the capability.
- **Capabilities live in closures.** `Apply`, `makeKAsset`, `Proof`, the state cells and the
  helpers are `new`-bound names that are never registered. The one unbundled handoff is the
  subject's `Apply` to `OracleFactory@"open"`; the case stores it in its closure and invokes
  it only from `execute`.
- **No names in state.** State maps hold strings, ints, maps, lists and `Nil`. A name in a
  state map would be readable through `get` and would turn a value field into a bearer
  capability. `check_capabilities.py` scans state sends for a direct `*Name`; a name nested
  inside a caller-supplied map is still a residual risk (RGA-066).

## Delegation graph

```text
installer ──register──▶ Root ──resolve──▶ factory URIs
factory ──create/propose/open──▶ entity URI (registry bundle)
entity ──arm──▶ state transition, guarded by deployerId/credential/party

claimant ──*dId──▶ Claim.validate ──makeKAsset──▶ KAsset URI
KAsset ──*Apply──▶ OracleFactory.open ──closure──▶ OracleCase
adjudicator ──*dId + proof──▶ OracleCase.decide ──stored decision──▶ OracleCase.execute
                                                       └──subjectApply──▶ Apply.applyDecision

subject ──*dId + requirement──▶ Credential.prove ──bundle+{*Proof} on proofCh──▶ consumer
```

## Authority table

| Check | Used by | Meaning |
|---|---|---|
| `caller-subject` | identity update, claim withdraw/resume, credential prove/revoke/renew/attest, KAsset nest, VP withdraw/proveValidated | The arm derives the REV address from the supplied `dId` and compares it to the stored subject. |
| `credential-proof` | claim/VP validate, KAsset approve/reject, Oracle decide | The caller must prove a credential for its own subject at the current height. |
| `party` | Oracle evidence, KAsset/VP openDispute, Oracle open | The derived address must be in the case's parties (and, for open, the adjudicator must not be). |
| `installer` | Root register, CredentialFactory issue | The derived address must be the installer or the genesis issuer. |
| `case-id` | KAsset/VP Apply | The invocation must name the case bound to the asset's dispute. |
| `runtime` | `deployerId`, registry, clock | The runtime supplies the name; it cannot be forged from data. |
| `none` | `Credential.check`, `proveApproved`, `execute`, `expire`, `close` | A read or clock arm. A consumer must not treat it as caller authentication. |

The static gate `tools/check_concurrency.py` forbids `Credential.check` as a commit authority.
`Issuer.authorize` now derives the caller from a `dId`; before the audit it accepted a
caller-supplied address and returned `(true, true)` to any deployer (RGA-048).

## What the audit found

The register has 38 rows over 19 `bundle+` expressions, three proof kinds, two `Apply`
capabilities, the Root installer and the seven ambient system channels. The blind HAZOP run
has 36 rows over nine capability nodes; the live suite has 12 probes (RT-024..RT-037;
RT-027/RT-033 are static checks in the register gate). The fixed defects with a live
regression:

- **K-Asset child anchor (RGA-049).** `nest` compared the genuine Claim's `kassetRef.uri`
  with the child's self-reported `get().uri`, then trusted the proof from the caller's
  `ref.uri`. A self-registered fake child could be nested. The fix compares the Claim's
  `kassetRef.uri` with `ref.uri`, resolves the child from that URI, and requires the proof
  `id`/`uri` to match. RT-032 flips from `(true, "ok")` to `claim kasset mismatch`.
- **Root register state (RGA-061).** `GenRoot.register` consumed `rootState` before
  authenticating the caller. A fresh channel in the `dId` position could block the auth
  continuation and commit the consumed directory cell. The arm now authenticates first and
  answers a failed auth with `not installer`. RT-037 checks `Root.keys` after a malformed
  register.
- **Issuer authorize (RGA-048).** The published arm trusted a caller-supplied address. It
  now takes a `dId` and derives the caller. RT-031 records the pre-fix `(true, true)` and the
  post-fix refusal.
- **Validator dispute (RGA-060).** `KAsset.openDispute` allowed the validator, but the case
  parties were `[claimant, approver]`, so the oracle refused the validator. The parties now
  include the validator. RT-036 opens a dispute as the validator.
- **K-Asset reply bundle (RGA-050).** `makeKAsset` returned `bundle+{*KAsset}` in a reply the
  Claim discarded. It now returns `(true, uri)`.
- **Issuer registry hold (RGA-069).** `CredentialFactory.issue` held `factoryState` across
  the asynchronous registry insert. The consume now follows the URI reply.
- **Installer checks (RGA-058, RGA-059).** `install.py` now rejects a dry-run placeholder and
  resolves all nine keys through Root before writing the manifest.
- **Client resolution (RGA-056, RGA-057).** `resolve_all`'s doc comment no longer claims a
  comparison it does not perform, and `Client::refresh_components` clears the cache after a
  reinstall or Root rotation.

Accepted hazards, with the reason in the register and the HAZOP adjudication:

- a forwarded proof is a bearer burn (the first taker wins) but cannot forge an acceptance;
- `proveApproved` is permissionless; parent-owned nesting uses its one-shot proof;
- an approval or validation survives revocation of the approver/validator credential;
- a child can have multiple parents (the nesting structure is a forest);
- a disputed K-Asset stays disputed if the case expires without a decision;
- provenance writers cannot be removed and provenance is advisory;
- the manifest's Root URI is an unsigned designation; signing or pinning it is a client
  extension;
- a `dId` passed to a helper delegates the caller's identity for as long as the helper holds
  the name.

## Lean

`spec/lean/RGen/Model/Capability.lean` models the abstract discipline:

- `RGen.Cap.no_holder_without_grant` — every holder has a grant path from a creator.
- `RGen.Cap.bundle_excludes_private` — a published bundle cannot invoke a private helper.
- `RGen.Cap.apply_case_bound` — an `Apply` capability changes only its bound case.
- `RGen.Cap.forward_burns_but_cannot_forge` — a forwarded proof can be taken, but the consumer
  check still binds subject, credential and height.
- `RGen.Cap.anchored_nest_requires_issued_child` — a nested child must be issued by the claim
  factory.
- `RGen.Cap.issuer_authorize_requires_issuer` — the dId-derived caller must be the issuer.
- `RGen.Cap.approval_survives_revocation` — the durable-approval hazard is a theorem.

The model abstracts names as `Nat` identifiers. It does not prove Rholang name unforgeability;
that is ASM-003 and ASM-011 in `spec/proofs/rigor.yaml`. In particular, it cannot prove that a
URI was inserted by the genuine factory; the anchor fix is a source-level check backed by
RT-032.

## Verify

```sh
make capabilities-check
make redteam-capabilities      # RGEN_EXPECT=fixed
make hazop-check
make check
```

A register row with `disposition: accepted` is a decision, not a pass. A `finding` is fixed
only when its probe or unit case is green on the devnet.
