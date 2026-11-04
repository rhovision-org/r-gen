# Quickstart

```sh
make venv
make build-check
make spec-check
make parse-check

export RHOLO_DIR=/home/patrick/RNodeRust
export RCASH_DIR=/home/patrick/Rholphin
make devnet-up
make rcash-keys
make rcash-bootstrap
make keys
make install
make unit-journey
```

The installer renders `__ROOT_URI__`, `__ADMINS__`, `__THRESHOLD__`,
`__GENESIS_ISSUER__`, `__RCASH_ROOT_URI__` and `__PLATFORM_OWNER__`. Root is deployed
first; every later term resolves it and registers its components.

If the r-cash rail is unavailable, the core identity, credential, work, K-Asset and token
primitives still install and run; only the payments adapter is inert.
