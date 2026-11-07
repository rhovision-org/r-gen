PY ?= .venv/bin/python
MDBOOK ?= mdbook
RHOLO_DIR ?= ../RNodeRust
NODE ?= http://localhost:40403
DEVNET_PREFIX ?= devnet
DEVNET_NODE_MEMORY ?= 8g
RGEN_CONTAINER ?= $(DEVNET_PREFIX)-bootstrap
NPM ?= npm
WEB ?= web
TESTNET_NODE ?= https://testnet.rhobot.net
TESTNET_ALLOW ?=

export RHOLO_DIR := $(abspath $(RHOLO_DIR))
export DEVNET_PREFIX
export DEVNET_NODE_MEMORY
export RGEN_CONTAINER

.PHONY: venv build build-check measure measure-check spec-check parse-check docs docs-check \
        check-arch check-captures check-placeholders check-money check-core-boundary \
        check-concurrency check-citations check-docs check-docs-links check-suites \
        check-pareto check-lean check-flows check-race-matrix check-arm-guards check-audit check-conformance check-hazop hazop-check check-capabilities capabilities-check guard-check style-check audit-control-flow probe-deploy-semantics redteam redteam-capabilities lean-build lean-audit lean-audit-coverage lean-check gen-core-vectors check-core-vectors \
        devnet-up devnet-wait down status keys install unit-identity unit-credentials \
        unit-claim unit-kasset unit-value unit-oracle unit-provenance unit-integration \
        unit-core unit-race unit-all verify \
        devnet-image devnet-doctor devnet-logs devnet-reset devnet-verify \
        devnet-test-smoke devnet-test-full devnet-test-nightly setup devnet-setup \
        client-lint client-test client-build client-wasm client-check \
        web-install web-dev web-build web-test web-typecheck web-wasm-smoke sync-manifest \
        testnet-preflight testnet-keys testnet-fund testnet-install testnet-verify \
        testnet-seed testnet-campaign demo-seed demo-verify \
        check ci clean

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

check-audit:
	$(PY) tools/check_audit.py --strict

check-conformance:
	$(PY) tools/check_conformance.py

check-hazop:
	$(PY) tools/check_hazop_runs.py

hazop-check: check-hazop

check-capabilities:
	$(PY) tools/check_capabilities.py

capabilities-check: check-capabilities

guard-check:
	$(PY) tools/check_guard_bridge.py

style-check:
	$(PY) tools/check_rholang_style.py

audit-control-flow:
	$(PY) tools/audit_rholang_control_flow.py

probe-deploy-semantics:
	$(PY) harness/probe_deploy_semantics.py

redteam:
	$(PY) harness/redteam_core.py

redteam-capabilities:
	$(PY) harness/redteam_capabilities.py

lean-build:
	cd spec/lean && lake build

gen-core-vectors:
	$(PY) tools/gen_vectors.py --write

check-core-vectors:
	$(PY) tools/check_core_vectors.py

lean-audit:
	$(PY) tools/check_lean.py --audit

lean-audit-coverage:
	$(PY) tools/check_lean.py --audit-coverage

lean-check: lean-build check-lean lean-audit lean-audit-coverage check-core-vectors

spec-check: build-check measure-check check-arch check-captures check-placeholders \
            check-money check-core-boundary check-concurrency check-citations \
            check-suites check-pareto check-lean check-flows check-race-matrix check-arm-guards check-audit check-conformance check-hazop check-capabilities guard-check style-check

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

devnet-image:
	cd $(RHOLO_DIR) && tools/devnet.sh build

devnet-doctor:
	$(PY) tools/devnet_doctor.py --rholo-dir $(RHOLO_DIR) --node $(NODE) \
		--memory $(DEVNET_NODE_MEMORY)

devnet-up:
	-cd $(RHOLO_DIR) && DEVNET_PREFIX=$(DEVNET_PREFIX) \
		DEVNET_NODE_MEMORY=$(DEVNET_NODE_MEMORY) tools/devnet.sh down
	cd $(RHOLO_DIR) && DEVNET_PREFIX=$(DEVNET_PREFIX) \
		DEVNET_NODE_MEMORY=$(DEVNET_NODE_MEMORY) tools/devnet.sh up --validators 1
	$(PY) harness/preflight.py --wait 300

devnet-wait:
	$(PY) harness/preflight.py --wait 300

devnet-logs:
	cd $(RHOLO_DIR) && DEVNET_PREFIX=$(DEVNET_PREFIX) tools/devnet.sh logs

devnet-verify: client-build
	target/debug/rgen-cli --node $(NODE) --manifest deployments/devnet.json \
		--shard /root --phlo-limit 8000000 --phlo-price 1 manifest verify --json

devnet-test-smoke:
	$(PY) harness/devnet_test.py --tier smoke

devnet-test-full:
	$(PY) harness/devnet_test.py --tier full

devnet-test-nightly:
	$(PY) harness/devnet_test.py --tier nightly

devnet-reset:
	cd $(RHOLO_DIR) && DEVNET_PREFIX=$(DEVNET_PREFIX) tools/devnet.sh down -v

down:
	cd $(RHOLO_DIR) && DEVNET_PREFIX=$(DEVNET_PREFIX) tools/devnet.sh down

status:
	@curl -s $(NODE)/api/v1/status | $(PY) -m json.tool || echo "devnet not running"

keys:
	$(PY) tools/keygen.py --out .devnet/keys.json

install:
	$(PY) harness/install.py --node $(NODE)

setup: devnet-up keys install sync-manifest
	@echo "setup: devnet, keys, contracts and web manifest are ready"

devnet-setup: setup

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
	cargo clippy -p rgen-core -p rgen-keystore -p rgen-sdk -p rgen-cli --all-targets -- -D warnings

client-test:
	cargo test -p rgen-core -p rgen-keystore -p rgen-sdk -p rgen-cli

client-wasm:
	cargo check -p rgen-wasm --target wasm32-unknown-unknown

client-build:
	cargo build -p rgen-cli

client-check: client-lint client-test client-wasm web-wasm-smoke web-test web-typecheck web-build

demo-seed:
	$(PY) harness/demo_seed.py --net devnet
	$(MAKE) sync-manifest

demo-verify:
	$(PY) harness/demo_verify.py

testnet-preflight:
	RGEN_NET=testnet $(PY) harness/testnet_preflight.py --node $(TESTNET_NODE) $(TESTNET_ALLOW)

testnet-keys:
	$(PY) harness/testnet_keys.py --fresh --keystores .testnet/keystores \
		--password rgen-testnet-demo

testnet-fund:
	RGEN_NET=testnet $(PY) harness/testnet_fund.py --node $(TESTNET_NODE) \
		$(TESTNET_ALLOW) --target deployer

testnet-install:
	RGEN_NET=testnet $(PY) harness/install_testnet.py --node $(TESTNET_NODE) $(TESTNET_ALLOW)

testnet-verify:
	target/debug/rgen-cli --node $(TESTNET_NODE) --manifest deployments/testnet.json \
		manifest verify --json
	$(PY) harness/demo_verify.py --catalogue deployments/catalogue.json \
		--manifest deployments/testnet.json

testnet-seed:
	RGEN_NET=testnet $(PY) harness/demo_seed.py --net testnet
	$(MAKE) sync-manifest

testnet-campaign: testnet-preflight testnet-keys testnet-fund testnet-install testnet-verify

web-install:
	cd $(WEB) && $(NPM) ci

web-dev:
	cd $(WEB) && $(NPM) run dev

web-build:
	cd $(WEB) && $(NPM) run build

web-test:
	cd $(WEB) && $(NPM) test

web-wasm-smoke:
	cd $(WEB) && $(NPM) run test:wasm

web-typecheck:
	cd $(WEB) && $(NPM) run typecheck

sync-manifest:
	cd $(WEB) && node scripts/sync-manifest.mjs

check: spec-check parse-check docs-check

ci: check unit-all

clean:
	rm -rf .venv __pycache__ harness/__pycache__ tools/__pycache__ \
		contracts/build/deploy/*.rho docs/book
