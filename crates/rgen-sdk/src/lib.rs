#![forbid(unsafe_code)]
//! Typed r-gen client over the pinned `rcash-sdk` signed-deploy path.
//!
//! The crate owns no wire protocol of its own: signing, deploy encoding, node HTTP and
//! finality polling come from `rcash-sdk`/`rcash-chain`. It adds the r-gen manifest,
//! arm templates, payload validation and typed operations shared by the CLI, the WASM
//! facade and the tests.

pub use rcash_chain;
pub use rcash_core;
pub use rcash_sdk;
pub use rgen_core;

pub mod client;
pub mod error;
pub mod models;
pub mod ops;
#[cfg(feature = "native")]
pub mod reader;
pub mod wire;

pub use client::{Client, ResolvedComponent, Write, WriteOutcome};
pub use error::{RefusalCode, SdkError};
pub use ops::factory_uri;
#[cfg(feature = "native")]
pub use reader::NodeReader;
pub use wire::{DeployReceipt, Read, ReadMeta, ReadSource};

/// Generate a fresh operation id. The caller supplies the timestamp so the browser can
/// use `Date.now()` and the CLI can use `SystemTime` without the SDK touching a clock.
pub fn new_op_id(prefix: &str, now_ms: i64) -> Result<rgen_core::OpId, SdkError> {
    let mut bytes = [0u8; 16];
    getrandom::fill(&mut bytes).map_err(|error| SdkError::Decode(error.to_string()))?;
    let random: String = bytes.iter().map(|byte| format!("{byte:02x}")).collect();
    rgen_core::OpId::new(format!("{prefix}-{now_ms}-{random}")).map_err(SdkError::from)
}
