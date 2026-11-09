//! `validate-payload` is the SDK's structural check, reachable from the Python harness.

use std::fs;
use std::process::Command;
use std::sync::atomic::{AtomicUsize, Ordering};

static NEXT: AtomicUsize = AtomicUsize::new(0);

fn run(kind: &str, body: &str, at_height: i64) -> std::process::Output {
    let sequence = NEXT.fetch_add(1, Ordering::Relaxed);
    let path = std::env::temp_dir().join(format!(
        "rgen-validate-{}-{sequence}-{kind}.json",
        std::process::id()
    ));
    fs::write(&path, body).expect("write the payload");
    let output = Command::new(env!("CARGO_BIN_EXE_rgen-cli"))
        .args([
            "validate-payload",
            kind,
            path.to_str().expect("utf-8 path"),
            "--at-height",
            &at_height.to_string(),
        ])
        .output()
        .expect("run rgen-cli");
    let _ = fs::remove_file(&path);
    output
}

const CLAIM: &str = r#"{
  "work": {"discipline": "process", "jurisdiction": "US-TX"},
  "statementHash": "aa",
  "definitionHash": "bb",
  "selectionCriteria": {"ctype": "Validator", "discipline": "process",
                        "jurisdiction": "US-TX", "role": "validator", "minLevel": 1},
  "quantity": {"unit": "validated-cases", "value": 5},
  "deadlineHeight": 10
}"#;

#[test]
fn a_valid_claim_passes() {
    let output = run("claim", CLAIM, 5);
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
}

#[test]
fn a_float_quantity_is_refused() {
    let body = CLAIM.replace("\"value\": 5", "\"value\": 5.5");
    let output = run("claim", &body, 5);
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("integer"));
}

#[test]
fn a_deadline_at_the_current_height_is_refused() {
    let body = CLAIM.replace("\"deadlineHeight\": 10", "\"deadlineHeight\": 5");
    let output = run("claim", &body, 5);
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("greater than"));
}
