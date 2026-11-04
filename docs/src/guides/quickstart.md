# Quickstart

```sh
make venv
make build-check
make parse-check
make check-core-boundary
make check-concurrency
make check-citations

export RHOLO_DIR=../RNodeRust
DEVNET_PREFIX=rgen make setup
make unit-core
make concurrency

# Web client
npm --prefix web ci
npm --prefix web run dev
```

`make setup` is `devnet-up keys install sync-manifest`. The node needs 8 GB
(`DEVNET_NODE_MEMORY=8g`); 4 GB is OOM-killed with exit 137. See
[Local devnet](devnet.md) for the pinned checkout, ports and troubleshooting.

The installer deploys seven terms in dependency order and wires factory URIs at install time:

```
00_root -> 10_identity -> 11_credentials -> 30_oracle -> 40_provenance
        -> 22_value -> 20_claim
```

There is no r-cash dependency in the core. KAT, payments, risk, panels, admin, handles and
metrics are extensions and are not installed by `make install`.

If the default `devnet-bootstrap` volume already exists, use `DEVNET_PREFIX=rgen` as shown;
it starts an isolated `rgen-bootstrap` on 40403/40405.
