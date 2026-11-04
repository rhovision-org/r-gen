# Quickstart

```sh
make venv
make build-check
make parse-check
make check-core-boundary
make check-concurrency
make check-citations

export RHOLO_DIR=../RNodeRust
DEVNET_PREFIX=rgen make devnet-up keys install
make unit-core
make concurrency
```

The installer deploys seven terms in dependency order and wires factory URIs at install time:

```
00_root -> 10_identity -> 11_credentials -> 30_oracle -> 40_provenance
        -> 22_value -> 20_claim
```

There is no r-cash dependency in the core. KAT, payments, risk, panels, admin, handles and
metrics are extensions and are not installed by `make install`.

If the default `devnet-bootstrap` volume already exists, use `DEVNET_PREFIX=rgen` as shown;
it starts an isolated `rgen-bootstrap` on 40403/40405.
