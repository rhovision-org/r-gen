#![forbid(unsafe_code)]
//! Pure RGen domain: identifiers, risk arithmetic, mint arithmetic, qualification matching
//! and the wire-facing models. No I/O and no chain client.

pub mod component;
pub mod error;
pub mod ids;
pub mod models;
pub mod payload;
pub mod qualification;
pub mod risk;
pub mod token;

pub use error::RgenError;

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
