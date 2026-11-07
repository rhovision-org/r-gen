# Local-devnet testing

> **Runner:** `harness/devnet_test.py`
> **Targets:** `make devnet-test-smoke`, `make devnet-test-full`, `make devnet-test-nightly`
> **Scope:** 7 contracts, end-to-end workflow, installer/Root/manifest, React/WASM client and
> Playwright. No testnet.

The local devnet is the behavioral gate. Static gates prove the build, the Lean model and the
style rules; the devnet proves the deployed contracts, the installer, the demo catalogue and
the browser client against a real node. A test that cannot reach a healthy node exits 2 and is
not a pass.

## Tiers

### T0 — static

```bash
make check
make lean-check
make web-typecheck
make web-test
make web-wasm-smoke
make web-build
```

`make client-check` (Rust fmt/clippy/tests/wasm) is optional for a devnet run and mandatory
before a release.

### T1 — preflight

```bash
git -C ../RNodeRust rev-parse HEAD   # expect e2d073dcd02f1e560ccb84749937138a1e184b0b
make devnet-doctor
```

`make devnet-image` builds from the checkout, not the pin. A dirty or ahead checkout is not the
verified node; `harness/devnet_test.py --strict-pin` fails on it. The doctor checks Docker, the
launcher, memory ≥ 6g and ports 40402/40403/40405.

`DEVNET_PREFIX` isolates container and volume names, not ports. Run one devnet on the default
ports, or use the port-shifted `devnet-rgenconf.sh` for a second net.

`make devnet-up` restarts an existing chain. `make devnet-reset` is the only from-genesis run;
it invalidates the manifest, the catalogue, the keys and every URI.

### T2 — smoke

```bash
make devnet-test-smoke
```

The orchestrator resets (unless `--no-reset`), starts the node, builds `rgen-cli`, creates
keys, installs the seven terms, runs `devnet-verify`, syncs the web manifest and runs
`unit-identity`, `unit-credentials` and `unit-claim`.

Pass criteria: install writes 9 components; `devnet-verify` reports `ok` with no missing keys
or URI mismatch; the three suites pass; `make status` still accepts deploys.

### T3 — full

```bash
make devnet-test-full
```

Adds:

- `make unit-all` — 10 suites, ~450s, writes `deployments/suite-results.json`;
- `RGEN_EXPECT=fixed make redteam` — no probe may classify `vulnerable`;
- `RGEN_EXPECT=fixed make redteam-capabilities` — RT-024..RT-037, no `vulnerable`;
- `make probe-deploy-semantics` — rollback-on-error and blocked-continuation commit;
- `make demo-seed` and `make demo-verify` — 14 catalogue entries re-read and cross-checked;
- `make web-test`, `web-typecheck`, `web-wasm-smoke`, `web-build`;
- `RGEN_E2E=1 npm --prefix web run test:e2e` — read journey;
- `RGEN_E2E=1 RGEN_E2E_JOURNEY=1 npm --prefix web run test:e2e` — full handshake;
- `make check` and `make lean-check`.

Pass: all ten suites `pass`; no red-team `vulnerable`; demo verify passes; both Playwright
journeys pass; static/Lean/docs green.

### T4 — nightly

```bash
make devnet-test-nightly
```

Adds a reinstall on the same chain and a 20-deploy soak (height must advance, no failed
deploy). The new Root must resolve 9/9. The old catalogue is verified against the
pre-reinstall manifest: a reinstall creates new factories and registries, so the new
ClaimFactory/ValuePropositionFactory cannot verify old entities; the old manifest can. The
runner copies the manifest to `.devnet/manifest-before-reinstall.json` before installing.

Recovery/fault injection is recorded as `skipped` until the fault-injection harness lands; a
skipped step is never a pass.

### T5 — manual

Testnet is opt-in with `make testnet-* TESTNET_ALLOW=--allow-live` and is not part of this
plan. Extension suites (payments, risk, panels, governance) are not implemented in the core.

## Coverage

| Area | Existing coverage |
|---|---|
| Identity | `unit_identity`, `concurrency_core` #11, RT-001; resume untested |
| Credential | `unit_credentials`, RT-004/008; `check`, issuer arms untested |
| Claim | `unit_claim`, `concurrency_core`, RT-002/006/007/023; resume untested |
| K-Asset | `unit_kasset`, `concurrency_core`, RT-013/014/032/036; many nest guards untested |
| Value proposition | `unit_value`, RT-020/021; comment/height/dispute refusals untested |
| Oracle | `unit_oracle`, `concurrency_core`, RT-009/010/012/022; evidence/execute/expire/close gaps |
| Provenance | `unit_provenance`, RT-011; create refusals untested |
| End-to-end | `unit_core`, `integration_core` |
| Web | `wasm-smoke`, `read.spec`, `handshake.spec`, 11 Vitest tests |
| Installer/Root | `install.py` 9/9 Root check, `install_testnet.py`; devnet `devnet-verify`; RT-029/037 |

## Gaps

**P1, devnet-reachable:** `Credential.check`; issuer `authorize`/`covers`/`get`;
`Identity.resume`; Root `register` refusals, `get`, `keys`; `Claim.resume` refusals, explicit
`expire`, Nil-window deadline, comment-after-withdraw; K-Asset prove/nest/dispute/applyDecision
guards; VP comment/height/dispute/applyDecision guards; oracle evidence-after-decide,
execute-before-decide, expire-success, close-expired, failed apply; missing race pairs; web
store wrong-network/stale-manifest tests; reinstall safety.

**P2, fault injection or intermediate state:** identity reserving/minted/expired resume; claim
validating→resume; nest phase-2 proof burn; deploy-atomicity pass/fail gate.

**Behavior to pin:** oracle `evidence` has no duplicate guard; `execution.attempts` is always
1; an unknown claim verdict maps to rejected; credential `attest` is not gated on active
status. A test should record the behavior and its disposition.

## Reliability

- `DEVNET_NODE_MEMORY=8g` when the host has it; 6g is the floor; 4g is a known exit-137.
- A fresh install can expose the Root a block before the manifest is readable; `devnet-verify`
  may fail once and then pass. The runner retries it twice and marks a recovered attempt
  `retried`, not failed.
- Do not run the suite storm beside other heavy jobs; the node is capped and swap-off.
- The faucet is one drip per address; the devnet native-REV transfer is the top-up path.
- Never reuse `.testnet/ops` across key sets; the cache keys on op id, not the signing key.
- After a reset, rerun `make devnet-test-full` (or `make setup demo-seed` and rebuild the web
  app); the old manifest and catalogue are invalid.

## Artifacts

- `deployments/devnet-test-<tier>.json` — step status, timings, pin, failures (gitignored).
- `deployments/suite-results.json`, `deployments/redteam-results.json`,
  `deployments/redteam-capabilities.json` (gitignored).
- `spec/audit/redteam.yaml`, `spec/audit/redteam-capabilities.yaml`,
  `spec/audit/deploy-semantics.{json,md}` (tracked audit records).
- `.devnet/`, `.demo/`, `web/test-results/`, `web/playwright-report/` (gitignored).
