# Local devnet

r-gen runs against an rholo devnet. The node launcher is in the pinned
`rchain-community/rchain-rust` checkout; this repository owns the contracts, keys and web
client, not the node image.

## Prerequisites

- Docker with at least 8 GB available to the node container.
- Python 3.12.
- Rust 1.95 with the `wasm32-unknown-unknown` target, and `wasm-pack` for the web client.
- Node 22 and npm.
- `mdbook` only for the documentation.

Check the local setup before starting a node:

```sh
make devnet-doctor
```

The doctor checks Docker, the checkout, the ports (40403 public, 40405 admin) and the
requested node memory. It does not start anything.

## Node checkout

The default is `../RNodeRust`:

```sh
git clone https://github.com/rchain-community/rchain-rust ../RNodeRust
cd ../RNodeRust
git checkout e2d073dcd02f1e560ccb84749937138a1e184b0b
```

Set `RHOLO_DIR` if the checkout is elsewhere. The pinned commit is recorded in
`configs/rholo.json`.

## Start

```sh
export RHOLO_DIR=../RNodeRust
DEVNET_PREFIX=rgen make devnet-up
make keys
make install
make sync-manifest
```

`DEVNET_PREFIX=rgen` keeps the container names away from any other devnet. The node is
`rgen-bootstrap`; public HTTP is <http://localhost:40403>, admin HTTP is
<http://localhost:40405>.

The one-command form is:

```sh
DEVNET_PREFIX=rgen make setup
```

It runs `devnet-up`, `keys`, `install` and `sync-manifest`.

## Memory

`DEVNET_NODE_MEMORY` defaults to `8g` in this repository. Do not lower it to `4g`: the
claim-validation deploy creates the K-Asset and the nest path is heavier than a simple
read, and the container is killed with exit 137 (OOM) before the suite finishes. The
verified setting is `8g`.

```sh
DEVNET_NODE_MEMORY=8g DEVNET_PREFIX=rgen make devnet-up
```

## Keys

`make keys` writes `.devnet/keys.json` with mode `0600`:

- `deployer` — the genesis issuer and installer signer.
- `alice`, `bob`, `carol`, `dave`, `erin` — demo actors.
- additional actor names for the behavioural suites.

The file is gitignored. Never commit it or copy a devnet key to the testnet.

## Install

`make install` renders the seven terms, captures the factory URIs from each deploy and
writes `deployments/devnet.json`:

```
00_root -> 10_identity -> 11_credentials -> 30_oracle -> 40_provenance
        -> 22_value -> 20_claim
```

The Root is the authority. A client resolves all nine keys through it; the manifest's
component copies are a convenience and a mismatch is treated as a stale manifest.

## Web client

```sh
npm --prefix web ci
npm --prefix web run dev
```

Open <http://localhost:5173>. Vite runs `build-wasm.mjs` and `sync-manifest.mjs` first.
If the file watcher hits `EMFILE` in a constrained environment, use the production build:

```sh
npm --prefix web run build
npm --prefix web run preview -- --port 5199
```

`npm run build` copies `deployments/devnet.json` and `deployments/catalogue.json` into
`web/public/`; a browser with an older cached manifest fetches the deployed one at boot.

## Seed the demo

```sh
make demo-seed
make demo-verify
```

`demo-seed` drives the real contracts: identities, Validator/Approver/Oracle credentials,
a value proposition, two claims and K-Assets (one approved, one disputed and upheld), an
oracle case and provenance with two anchors. It hashes the documents in
`harness/demo/artifacts/bridge-deck-2026/` and writes:

- `deployments/catalogue.json` — real URIs and labels for the Overview page.
- `.demo/keystores-devnet/` — encrypted keystores for issuer, alice, bob, carol and dave.
- `.demo/seed-devnet.json` — actor addresses, credential URIs and the keystore password.

The demo password is `rgen-demo-password`. The keystores are gitignored. `demo-verify`
re-reads every catalogue URI and checks the claim/K-Asset/case/provenance relationships in
both directions.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Container exits 137 | node memory below the contract workload | `DEVNET_NODE_MEMORY=8g` |
| Port 40403 or 40405 already in use | another devnet is running | `DEVNET_PREFIX=other make down`, or stop it |
| `Root resolved (0/9)` in the app | stale cached manifest or a reinstall | rebuild the app, or paste `deployments/devnet.json` in Settings |
| `explore-deploy returned no value` | the URI is from an older Root | reinstall and resync the manifest |
| `preCharge: insufficient funds` | the signing account has no REV | use the faucet or the funded deployer key |
| Suite exits 2 | no healthy devnet | start the node and run `make devnet-wait` |

## Teardown

```sh
make down           # stop the containers, keep the volumes
make devnet-reset   # stop and delete the volumes; the chain starts from genesis
```

A reset invalidates the manifest, the keys and every catalogue URI. Re-run
`make setup demo-seed` and rebuild the web app after a reset.
