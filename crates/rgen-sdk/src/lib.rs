#![forbid(unsafe_code)]
//! Typed client facade for RGen on rholo.
//!
//! The deploy/signing/transport path is inherited from the pinned `rcash-sdk` and
//! `rcash-chain` crates rather than reimplemented here. This crate adds the RGen domain
//! view and a small HTTP reader for the node's public API.

pub use rcash_chain;
pub use rcash_core;
pub use rcash_sdk;
pub use rgen_core;

pub mod client;
pub mod error;

pub use client::Client;
pub use error::SdkError;
