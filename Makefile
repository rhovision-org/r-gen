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
        check-concurrency check-citations check-docs check-docs-links check-suites \
        check-pareto check-lean check-flows check-race-matrix check-arm-guards lean-build lean-audit lean-check gen-core-vectors check-core-vectors \
        devnet-up devnet-wait down status keys install unit-identity unit-credentials \
        unit-claim unit-kasset unit-value unit-oracle unit-provenance unit-integration \
        unit-core unit-race unit-all verify \
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

check-docs:
	$(PY) tools/check_docs.py

check-docs-links:
	$(PY) tools/check_docs_links.py

check-suites:
	$(PY) tools/check_suites.py

check-pareto:
	$(PY) tools/check_pareto.py

check-lean:
	$(PY) tools/check_lean.py

check-flows:
	$(PY) tools/check_flows.py

check-race-matrix:
	$(PY) tools/check_race_matrix.py

check-arm-guards:
	$(PY) tools/check_arm_guards.py

lean-build:
	cd spec/lean && lake build

gen-core-vectors:
	$(PY) tools/gen_vectors.py --write

check-core-vectors:
	$(PY) tools/check_core_vectors.py

lean-audit:
	$(PY) tools/check_lean.py --audit

lean-check: lean-build check-lean lean-audit check-core-vectors

spec-check: build-check measure-check check-arch check-captures check-placeholders \
            check-money check-core-boundary check-concurrency check-citations \
            check-suites check-pareto check-lean check-flows check-race-matrix check-arm-guards

parse-check:
	rm -f .devnet/rendered/*.rho
	$(PY) harness/install.py --dry-run
	RCHAIN_RUST_DIR=$(RHOLO_DIR) tools/parse_check.sh contracts/build/deploy/*.rho \
		.devnet/rendered/*.rho

docs:
	$(PY) tools/sync_papers.py
	$(MDBOOK) build

docs-check: check-docs check-docs-links check-citations
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

unit-identity:
	$(PY) harness/unit_identity.py

unit-credentials:
	$(PY) harness/unit_credentials.py

unit-claim:
	$(PY) harness/unit_claim.py

unit-kasset:
	$(PY) harness/unit_kasset.py

unit-value:
	$(PY) harness/unit_value.py

unit-oracle:
	$(PY) harness/unit_oracle.py

unit-provenance:
	$(PY) harness/unit_provenance.py

unit-integration:
	$(PY) harness/integration_core.py

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
