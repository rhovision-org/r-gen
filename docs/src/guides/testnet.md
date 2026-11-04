# Public testnet

The public rholo testnet is a disposable, no-value chain. It is useful for showing the web
client away from a laptop devnet; it is not a production network and it is not an audit.

## Current identity

| Field | Value |
|---|---|
| Node (HTTPS) | <https://testnet.rhobot.net> |
| Direct HTTP | <http://167.99.43.214:40403> |
| Network id | `testnet-133b1d307b175012` |
| Shard | `/testnet` |
| Genesis | `133b1d307b1750129cf0cfb69c4c8f950da21c4e8db2a6a076464d0ccfd98d44` |
| Faucet | <https://testnet.rhobot.net/api/faucet>, 0.3 REV once per address |
| Phlo | price 1; the browser uses 8,000,000 as a per-deploy ceiling |
| Observed node build | `0a1e02362a7c34e474e068ffd47469c8d4be707a` |

These values are pinned in `configs/testnet.json`. A different network id, shard or genesis
is a different chain: stop and re-run the campaign. A different node build is a warning,
not a chain-identity failure.

## Safety rules

1. Never reuse a devnet key. `testnet-keys` rejects a key file whose public keys appear in
   `.devnet/keys.json`.
2. Every live command is opt-in. Pass `TESTNET_ALLOW=--allow-live`; the scripts refuse a
   rhobot endpoint without it.
3. Do not retry a value-moving deploy blindly. The installer keeps a write-ahead op cache
   and stops on an unknown outcome; reconcile the deploy id before retrying.
4. Do not reuse the manifest or catalogue after a reset. The old Root resolves to nothing.
5. A blocked or refused stage is not a pass. Read the refusal and stop.

r-gen remains no-value software. The testnet is disposable; nothing here changes the
audit status of the contracts.

## Campaign

```sh
# Read-only identity and key preflight.
make testnet-preflight TESTNET_ALLOW=--allow-live

# Fresh keys, mode 0600, plus encrypted browser keystores.
make testnet-keys

# One faucet drip for the installer; the seed funds the actors separately.
make testnet-fund TESTNET_ALLOW=--allow-live

# Render, sign and install the seven terms, then verify every Root key.
make testnet-install TESTNET_ALLOW=--allow-live

# Seed the bridge-inspection scenario and sync the web manifest.
make testnet-seed

# Re-read the manifest and every catalogue URI.
make testnet-verify
```

`testnet-keys` writes:

- `.testnet/keys.json` — plaintext campaign keys, mode `0600`, gitignored.
- `.testnet/keystores/` — encrypted Web3 v3 keystores for the browser, gitignored.
  The password is `rgen-testnet-demo`.

`testnet-install` writes `deployments/testnet.json`. The manifest contains public registry
URIs only. Commit it after a verified install if the web app should ship with a testnet
target; never commit `.testnet/keys.json` or the keystores.

## Deploy costs and the faucet

The faucet gives 0.3 REV once per address. A deploy precharges its phlo ceiling and refunds
the unused part, so a 0.3 REV account can submit a deploy with an 8,000,000 phlo ceiling
(0.08 REV precharge) and pay only the measured cost. The installer funds the deployer first;
the seed lets each actor faucet its own address.

The public node also limits free `explore-deploy` reads with an execution budget. When the
budget is exhausted the node returns 429 and the body `explore execution budget exhausted`.
The web client retries with backoff and reports the node message; a funded signed deploy or
a new block replenishes the budget. This is a property of the public host, not of the
contracts. The local devnet has no such budget.

## Web client

Point Settings at `https://testnet.rhobot.net`. The app fetches `testnet.json` from the
build, checks the pinned network id and shard, and resolves all nine Root keys before
enabling writes. Import the testnet keystores from `.testnet/keystores/`; the demo flow is
the same as the devnet flow.

If the manifest is missing, install first and run `make sync-manifest`, then rebuild the
app. Settings also accepts a pasted manifest.

## After a reset

A reset (new genesis or a new network id) invalidates everything:

1. Re-run `make testnet-preflight TESTNET_ALLOW=--allow-live`.
2. Rotate keys with `make testnet-keys`.
3. Reinstall, re-seed and re-verify.
4. Rebuild the app so it serves the new manifest and catalogue.

Old catalogue entries show as missing. That is the intended behaviour; the UI never keeps a
stale status.
