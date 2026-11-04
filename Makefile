PY ?= .venv/bin/python
MDBOOK ?= mdbook
RHOLO_DIR ?= ../RNodeRust
NODE ?= http://localhost:40403
DEVNET_PREFIX ?= devnet
RGEN_CONTAINER ?= $(DEVNET_PREFIX)-bootstrap

export RHOLO_DIR := $(abspath $(RHOLO_DIR))
export DEVNET_PREFIX
export RGEN_CONTAINER

.PHONY: venv build build-check measure measure-check spec-check parse-check docs docs-check \
        check-arch check-captures check-placeholders check-money check-core-boundary \
        check-concurrency check-citations check-paper-licenses check-docs check-suites \
        devnet-up devnet-wait down status keys install unit-core unit-race unit-all verify \
        client-lint client-test client-build check ci clean

venv:
	python3 -m venv .venv
	$(PY) -m pip -q install --upgrade pip
	$(PY) -m pip -q install -r harness/requirements.txt

build:
	$(PY) tools/build_contracts.py

build-check:
	$(PY) tools/build_contracts.py --check

measure:
	$(PY) tools/measure_contracts.py --write

measure-check:
	$(PY) tools/measure_contracts.py --check

check-arch:
	$(PY) tools/check_arch.py

check-captures:
	$(PY) tools/check_captures.py

check-placeholders:
	$(PY) tools/check_placeholders.py

check-money:
	$(PY) tools/check_money.py

check-core-boundary:
	$(PY) tools/check_core_boundary.py

check-concurrency:
	$(PY) tools/check_concurrency.py

check-citations:
	$(PY) tools/check_citations.py

check-paper-licenses:
	$(PY) tools/check_paper_licenses.py

check-docs:
	$(PY) tools/check_docs.py

check-suites:
	$(PY) tools/check_suites.py

spec-check: build-check measure-check check-arch check-captures check-placeholders \
            check-money check-core-boundary check-concurrency check-citations \
            check-suites

parse-check:
	rm -f .devnet/rendered/*.rho
	$(PY) harness/install.py --dry-run
	RCHAIN_RUST_DIR=$(RHOLO_DIR) tools/parse_check.sh contracts/build/deploy/*.rho \
		.devnet/rendered/*.rho

docs:
	$(PY) tools/sync_papers.py
	$(MDBOOK) build

docs-check: check-docs check-citations check-paper-licenses
	$(PY) tools/sync_papers.py
	$(MDBOOK) build

devnet-up:
	-cd $(RHOLO_DIR) && DEVNET_PREFIX=$(DEVNET_PREFIX) tools/devnet.sh down
	cd $(RHOLO_DIR) && DEVNET_PREFIX=$(DEVNET_PREFIX) tools/devnet.sh up --validators 1
	$(PY) harness/preflight.py --wait 300

devnet-wait:
	$(PY) harness/preflight.py --wait 300

down:
	cd $(RHOLO_DIR) && DEVNET_PREFIX=$(DEVNET_PREFIX) tools/devnet.sh down

status:
	@curl -s $(NODE)/api/v1/status | $(PY) -m json.tool || echo "devnet not running"

keys:
	$(PY) tools/keygen.py --out .devnet/keys.json

install:
	$(PY) harness/install.py --node $(NODE)

unit-core:
	$(PY) harness/unit_core.py

unit-race:
	$(PY) harness/concurrency_core.py

unit-all:
	$(PY) harness/run_core_suites.py

verify: build-check parse-check install unit-all
	@echo "verify: core build, parse, install and suites passed"

client-lint:
	cargo fmt --all -- --check
	cargo clippy -p rgen-core -p rgen-sdk -p rgen-cli --all-targets -- -D warnings

client-test:
	cargo test -p rgen-core -p rgen-sdk

client-build:
	cargo build -p rgen-cli

check: spec-check parse-check docs-check

ci: check unit-all

clean:
	rm -rf .venv __pycache__ harness/__pycache__ tools/__pycache__ \
		contracts/build/deploy/*.rho docs/book
