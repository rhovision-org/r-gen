# Web client

The web client is a reference application, not a mock. It reads the deployed contracts and
signs real deploys through the same signed-deploy path as the CLI.

- **Stack:** Rust core → WASM (`rgen-wasm`), React 18, Vite, strict TypeScript, HashRouter,
  react-query, zustand, plain CSS. There is no backend.
- **Wallet:** secp256k1 signing inside WASM. The browser stores a Web3 Secret Storage v3
  keystore in IndexedDB; the private key never crosses into JavaScript.
- **Network:** devnet, public testnet, or a custom node. Settings selects the profile and
  accepts a pasted manifest. The app resolves all nine Root keys before writes are enabled.
- **Root pinning:** the devnet profile may trust its local manifest. The testnet and custom
  profiles require `VITE_RGEN_ROOT_URI` at build time and refuse a fetched, cached or
  pasted manifest whose `root_uri` differs. Set it before `npm run build`; an unpinned
  non-devnet build fails closed.
- **No indexer:** the chain is the backend. Lists are the local journal, pasted share links,
  and the seeded catalogue. Every detail page re-reads its entity.

## Run

```sh
npm --prefix web ci
npm --prefix web run dev
```

`predev` builds the WASM module and copies the deployment manifest and catalogue into
`web/public/`. Open <http://localhost:5173>.

If Vite's watcher hits `EMFILE`, use the production build:

```sh
npm --prefix web run build
npm --prefix web run preview -- --port 5199
```

## Screens

| Route | Purpose |
|---|---|
| `/` | network identity, finalized height, Root readiness, your identity, URI lookup, catalogue |
| `/claims` | journaled claims, open by URI, create a claim |
| `/claims/new` | claim form; free text is hashed locally |
| `/claims/:uri` | claim state, comments, validate/resume/comment/withdraw/expire |
| `/kassets` | journaled K-Assets, open by URI |
| `/kassets/:uri` | approve/reject, nest, open dispute, children, revocation |
| `/credentials` | credentials, open by URI, issue |
| `/credentials/issue` | genesis-issuer form |
| `/credentials/:uri` | check, revoke, renew, attest, attestations and renewals |
| `/value` | value propositions, open by URI, propose |
| `/value/new` | proposition form |
| `/value/:uri` | validate, comment, withdraw, open dispute |
| `/cases` | oracle cases, open by URI |
| `/cases/:uri` | evidence, decide, execute, expire, close; execution receipt |
| `/provenance` | provenance records, open by URI, create |
| `/provenance/new` | asset reference and writers |
| `/provenance/:uri` | anchors, comment, verify |
| `/identity` | own identity; create or update the three profile hashes |
| `/activity` | local journal with deploy ids and reconcile |
| `/settings` | network preset, manifest, wallet profiles, faucet, REV balance, components |

Cases are never created from a standalone form: `OracleFactory.open` takes a private
subject capability and is reached through a K-Asset or value-proposition dispute.

## Wallets and profiles

`Unlock` has three modes:

- **Unlock** a saved keystore in this browser.
- **Create** a fresh wallet; the encrypted keystore downloads and is also stored locally.
- **Import** a keystore JSON, for example a demo or testnet keystore.

Each imported or created wallet is a profile. Locking and unlocking a different profile
moves between real keys; there is no synthetic actor switch.

The native REV balance and faucet are in Settings. The faucet is a node route, not a
contract: devnet serves `/api/v1/faucet`, the testnet serves `/api/faucet`. One drip per
address. A write needs REV for phlo; the app reports `preCharge: insufficient funds` if the
wallet is empty.

## Demonstration flow

1. Start a devnet and run `make demo-seed` (see [Local devnet](devnet.md)).
2. Open the app. The Overview shows the seeded catalogue with live statuses.
3. Import `.demo/keystores-devnet/alice.json` (password `rgen-demo-password`).
4. Create a claim. It appears at `/claims/rho:id:…`; copy the share link.
5. Lock, import `bob.json`, open the share link, and validate with Bob's Validator
   credential URI from `.demo/seed-devnet.json`.
6. Lock, import `carol.json`, open the new K-Asset, approve with Carol's Approver
   credential URI.
7. Lock, import `alice.json`, open the K-Asset, and open a dispute naming Dave and his
   Oracle credential. Lock, import `dave.json`, decide and execute.
8. As Alice, create provenance for the K-Asset and anchor the report text. Verify the hash.

Every step is a signed deploy. The entity page re-reads the contract after the receipt; a
refusal is displayed with its reason and the entity is re-read because a refusal can still
change state (an expired claim, a failed execution receipt).

## Network profiles

- **devnet** — `http://localhost:40403`, shard `/root`.
- **testnet** — `https://testnet.rhobot.net`, shard `/testnet`, pinned network
  `testnet-133b1d307b175012`, manifest `testnet.json`. See [Public testnet](testnet.md).
- **custom** — any node URL; the shard is `/root` and the user supplies the manifest.

The catalogue is network-scoped. A catalogue whose `networkId`, shard or Root differs from
the connected chain is refused rather than shown with stale labels.

## Tests

```sh
npm --prefix web run test        # Vitest
npm --prefix web run test:wasm   # offline WASM smoke
npm --prefix web run typecheck
npm --prefix web run build
```

Playwright is opt-in:

```sh
RGEN_E2E=1 npm --prefix web run test:e2e
```

The read spec needs a seeded devnet. The full handshake spec additionally needs
`RGEN_E2E_JOURNEY=1` and the `.demo/keystores-devnet/` bundle. The suite never asserts
success from the UI alone: it waits for finality and re-reads the entity.
