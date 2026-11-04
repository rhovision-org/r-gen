#!/usr/bin/env bash
# Parse Rholang files with the target node's own parser.
#
#   tools/parse_check.sh contracts/build/*.rho
#
# RCHAIN_RUST_DIR defaults to ../RNodeRust. The crate is cached under .devnet/ so the
# repository does not vendor the node. RUSTC_BOOTSTRAP is needed only because the node
# workspace pins a nightly feature in one dependency.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RCHAIN_RUST_DIR="${RCHAIN_RUST_DIR:-$ROOT/../RNodeRust}"
CRATE="$ROOT/.devnet/parse-check"
mkdir -p "$CRATE/src"

ARGS=()
for arg in "$@"; do
  ARGS+=("$(cd "$(dirname "$arg")" && pwd)/$(basename "$arg")")
done

cat > "$CRATE/Cargo.toml" <<EOF
[package]
name = "rshare-parse"
version = "0.1.0"
edition = "2021"

[dependencies]
rchain-rholang = { path = "$(cd "$RCHAIN_RUST_DIR" && pwd)/rholang" }
EOF

cat > "$CRATE/src/main.rs" <<'EOF'
use std::{env, fs};
fn main() {
    let mut bad = 0;
    for path in env::args().skip(1) {
        let text = fs::read_to_string(&path).unwrap();
        match rchain_rholang::parser::parse(&text) {
            Ok(_) => println!("OK   {path}"),
            Err(e) => { bad += 1; println!("FAIL {path}: {e:?}"); }
        }
    }
    std::process::exit(if bad == 0 { 0 } else { 1 });
}
EOF

cd "$CRATE"
RUSTC_BOOTSTRAP=1 CC="${CC:-/usr/bin/gcc}" cargo build --release --quiet
exec "$CRATE/target/release/rshare-parse" "${ARGS[@]}"
