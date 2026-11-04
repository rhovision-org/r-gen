PY ?= .venv/bin/python
MDBOOK ?= mdbook
RCASH_DIR ?= ../Rholphin
RHOLO_DIR ?= ../RNodeRust
NODE ?= http://localhost:40403
# A second isolated network can be brought up beside a stale default devnet:
#   DEVNET_PREFIX=rgen make devnet-up install unit-all
DEVNET_PREFIX ?= devnet
RGEN_CONTAINER ?= $(DEVNET_PREFIX)-bootstrap

export RCASH_DIR := $(abspath $(RCASH_DIR))
export RHOLO_DIR := $(abspath $(RHOLO_DIR))
export DEVNET_PREFIX
export RGEN_CONTAINER

.PHONY: venv build build-check measure measure-check spec-check parse-check \
        docs docs-serve docs-check devnet devnet-up devnet-wait down status \
        rcash-keys rcash-bootstrap keys install setup \
        unit-root unit-identity unit-credentials unit-token unit-work unit-kasset \
        unit-provenance unit-risk unit-payments unit-oracle unit-dispute \
        unit-conservation unit-adversarial unit-journey unit-all \
        check ci clean client-lint client-test client-build check-arch \
        check-captures check-placeholders check-money check-suites check-docs \
        check-flows check-vectors formal-check

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

check-suites:
	$(PY) tools/check_suites.py

check-docs:
	$(PY) tools/check_docs.py
	$(MDBOOK) build

check-flows:
	$(PY) tools/check_flows.py

check-vectors:
	$(PY) tools/check_vectors.py

spec-check: build-check measure-check check-arch check-captures check-placeholders \
            check-money check-suites

parse-check:
	$(PY) harness/install.py --dry-run
	RCHAIN_RUST_DIR=$(RHOLO_DIR) tools/parse_check.sh contracts/build/deploy/*.rho .devnet/rendered/*.rho

formal-check: check-flows check-vectors

docs:
	$(MDBOOK) build

docs-serve:
	$(MDBOOK) serve --open

docs-check: check-docs

devnet:
	cd $(RHOLO_DIR) && tools/devnet.sh up --validators 1

devnet-up:
	-cd $(RHOLO_DIR) && tools/devnet.sh down -v
	cd $(RHOLO_DIR) && tools/devnet.sh up --validators 1
	$(PY) harness/preflight.py --wait 300

devnet-wait:
	$(PY) harness/preflight.py --wait 300

down:
	cd $(RHOLO_DIR) && tools/devnet.sh down -v

status:
	@curl -s $(NODE)/api/v1/status | $(PY) -m json.tool || echo "devnet not running"

rcash-keys:
	$(MAKE) -C $(RCASH_DIR) keys RHOLO_DIR=$(RHOLO_DIR)

rcash-bootstrap:
	$(PY) harness/rcash_bootstrap.py --rcash $(RCASH_DIR) --node $(NODE)

keys:
	$(PY) tools/keygen.py --out .devnet/keys.json \
		--from-path $(RCASH_DIR)/.devnet/keys.json

install:
	$(PY) harness/install.py --node $(NODE)

setup: devnet-up rcash-keys rcash-bootstrap keys install

unit-root:
	$(PY) harness/unit_root.py
unit-identity:
	$(PY) harness/unit_identity.py
unit-credentials:
	$(PY) harness/unit_credentials.py
unit-token:
	$(PY) harness/unit_token.py
unit-work:
	$(PY) harness/unit_work.py
unit-kasset:
	$(PY) harness/unit_kasset.py
unit-provenance:
	$(PY) harness/unit_provenance.py
unit-risk:
	$(PY) harness/unit_risk.py
unit-payments:
	$(PY) harness/unit_payments.py
unit-oracle:
	$(PY) harness/unit_oracle.py
unit-dispute:
	$(PY) harness/unit_dispute.py
unit-conservation:
	$(PY) harness/unit_conservation.py
unit-adversarial:
	$(PY) harness/unit_adversarial.py
unit-journey:
	$(PY) harness/unit_journey.py

unit-all:
	$(PY) harness/run_suites.py

client-lint:
	cargo fmt --all -- --check
	cargo clippy -p rgen-core -p rgen-sdk -p rgen-cli --all-targets -- -D warnings

client-test:
	cargo test -p rgen-core -p rgen-sdk

client-build:
	cargo build -p rgen-cli

check: spec-check parse-check docs-check formal-check

ci: check unit-all

clean:
	rm -rf .venv __pycache__ harness/__pycache__ tools/__pycache__ contracts/build/*.rho docs/book
