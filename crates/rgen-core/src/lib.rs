#![forbid(unsafe_code)]
//! Pure r-gen client types: the live component catalogue, manifests, payload validation
//! and safe JSON-to-Rholang rendering. No I/O and no chain client.
//!
//! The risk/token/KAT modules are the pre-Pareto extension prototype. They are kept for
//! the CLI's arithmetic commands and the historical vectors; the web client does not use
//! them.

pub mod component;
pub mod error;
pub mod ids;
pub mod manifest;
pub mod models;
pub mod op;
pub mod payload;
pub mod qualification;
pub mod render;
pub mod requests;
pub mod risk;
pub mod token;

pub use component::ComponentKey;
pub use error::{Result, RgenError};
pub use manifest::Manifest;
pub use op::OpId;
pub use rcash_core::assets::RegistryUri;

/// KAT has eight decimals.
pub const KAT_DECIMALS: u8 = 8;
/// One KAT in base units.
pub const KAT_BASE: u64 = 100_000_000;
/// The unit mint: 100 KAT for a full-quality K-Asset.
pub const UNIT_MINT: u64 = 100 * KAT_BASE;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn constants_are_consistent() {
        assert_eq!(UNIT_MINT, 10_000_000_000);
        assert_eq!(UNIT_MINT / KAT_BASE, 100);
    }
}
