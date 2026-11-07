//! The typed r-gen chain client.
//!
//! It reuses `rcash-sdk`/`rcash-chain` for signing, deploy encoding, node HTTP, finality
//! polling and `RhoValue` decoding. A reader has no key; a signer owns one and can submit
//! deploys. The key never leaves this process.

use std::collections::BTreeMap;
use std::sync::Mutex;

use rcash_chain::node::pool::{DiscoveryMode, PoolOptions};
use rcash_chain::node::{DeployStatus, NodeClient};
use rcash_chain::rho_expr::RhoValue;
use rcash_chain::KeyPair;
use rcash_sdk::Client as RcashClient;

use rgen_core::{ComponentKey, Manifest, RegistryUri};

use crate::error::{Result, SdkError};
use crate::models;
use crate::wire::{self, DeployReceipt, Read};

/// A component resolved through the Root.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ResolvedComponent {
    pub uri: RegistryUri,
    pub version: i64,
}

/// A successful write and its receipt.
#[derive(Clone, Debug, PartialEq)]
pub struct Write<T> {
    pub value: T,
    pub receipt: DeployReceipt,
}

/// A write that reached a finalized block. The contract may still have refused it.
#[derive(Clone, Debug, PartialEq)]
pub enum WriteOutcome<T> {
    Accepted(Write<T>),
    Refused {
        reason: String,
        code: crate::error::RefusalCode,
        receipt: DeployReceipt,
    },
}

/// The r-gen client.
pub struct Client {
    inner: RcashClient,
    manifest: Manifest,
    shard: String,
    phlo_limit: i64,
    phlo_price: i64,
    cache: Mutex<BTreeMap<ComponentKey, ResolvedComponent>>,
}

impl Client {
    pub const DEFAULT_PHLO_LIMIT: i64 = 8_000_000;
    pub const DEFAULT_PHLO_PRICE: i64 = 1;
    pub const DEFAULT_SHARD: &'static str = "/root";

    pub fn reader(node: &str, manifest: Manifest) -> Result<Self> {
        Self::build(
            node,
            manifest,
            None,
            Self::DEFAULT_SHARD,
            Self::DEFAULT_PHLO_LIMIT,
            Self::DEFAULT_PHLO_PRICE,
        )
    }

    pub fn new(node: &str, manifest: Manifest, key: KeyPair) -> Result<Self> {
        Self::build(
            node,
            manifest,
            Some(key),
            Self::DEFAULT_SHARD,
            Self::DEFAULT_PHLO_LIMIT,
            Self::DEFAULT_PHLO_PRICE,
        )
    }

    pub fn with_node(
        node: NodeClient,
        manifest: Manifest,
        key: Option<KeyPair>,
        shard: &str,
        phlo_limit: i64,
        phlo_price: i64,
    ) -> Result<Self> {
        let inner = RcashClient::with_node(node, key)
            .with_shard(shard)
            .with_phlo(phlo_limit, phlo_price);
        Ok(Self {
            inner,
            manifest,
            shard: shard.to_string(),
            phlo_limit,
            phlo_price,
            cache: Mutex::new(BTreeMap::new()),
        })
    }

    fn build(
        node: &str,
        manifest: Manifest,
        key: Option<KeyPair>,
        shard: &str,
        phlo_limit: i64,
        phlo_price: i64,
    ) -> Result<Self> {
        let node_client = node_client(node, shard)?;
        Self::with_node(node_client, manifest, key, shard, phlo_limit, phlo_price)
    }

    pub fn with_network(mut self, shard: &str, phlo_limit: i64, phlo_price: i64) -> Self {
        self.set_network(shard, phlo_limit, phlo_price);
        self
    }

    pub fn set_network(&mut self, shard: &str, phlo_limit: i64, phlo_price: i64) {
        self.inner
            .set_network(shard.to_string(), phlo_limit, phlo_price);
        self.shard = shard.to_string();
        self.phlo_limit = phlo_limit;
        self.phlo_price = phlo_price;
    }

    pub fn key(&self) -> Option<&KeyPair> {
        self.inner.key()
    }

    pub fn manifest(&self) -> &Manifest {
        &self.manifest
    }

    pub fn shard(&self) -> &str {
        &self.shard
    }

    pub fn phlo(&self) -> (i64, i64) {
        (self.phlo_limit, self.phlo_price)
    }

    pub fn node(&self) -> &NodeClient {
        self.inner.node()
    }

    pub fn has_key(&self) -> bool {
        self.inner.key().is_some()
    }

    pub fn address(&self) -> Result<String> {
        Ok(self.inner.address()?)
    }

    pub async fn height(&self) -> Result<i64> {
        Ok(self.inner.height().await?)
    }

    pub async fn status(&self) -> Result<serde_json::Value> {
        Ok(self.inner.node().status().await?)
    }

    /// The node's view of a deploy. Used to reconcile a journal entry.
    pub async fn deploy_status(&self, deploy_id: &str) -> Result<DeployStatus> {
        Ok(self.inner.node().deploy_status(deploy_id).await?)
    }

    /// Native REV balance for an address. Free read; the reply is a bare integer.
    pub async fn native_rev_balance(&self, address: &str) -> Result<Read<i64>> {
        let term = wire::native_rev_balance_term(address)?;
        let (value, meta) = wire::explore_value(&self.inner, &term).await?;
        Ok(Read {
            value: value.as_int().unwrap_or_default(),
            meta,
        })
    }

    /// Resolve one component through the Root. Results are cached for the life of the
    /// client; call `refresh_components` after a reinstall.
    pub async fn resolve(&self, key: ComponentKey) -> Result<ResolvedComponent> {
        if let Some(hit) = self
            .cache
            .lock()
            .expect("component cache lock")
            .get(&key)
            .cloned()
        {
            return Ok(hit);
        }
        let term = wire::resolve_term(self.manifest.root_uri(), key.key())?;
        let (value, _meta) = wire::explore_value(&self.inner, &term).await?;
        let values = wire::decode_reply(&value)?;
        let uri = values
            .first()
            .and_then(RhoValue::as_str)
            .ok_or_else(|| SdkError::Decode(format!("resolve({key}) has no uri")))?;
        let version = values.get(1).and_then(RhoValue::as_int).unwrap_or(1);
        let resolved = ResolvedComponent {
            uri: RegistryUri::new(uri)?,
            version,
        };
        self.cache
            .lock()
            .expect("component cache lock")
            .insert(key, resolved.clone());
        Ok(resolved)
    }

    /// Resolve every component through the Root. The manifest copies are not authority.
    pub async fn resolve_all(&self) -> Result<BTreeMap<ComponentKey, ResolvedComponent>> {
        let mut resolved = BTreeMap::new();
        for key in ComponentKey::ALL {
            resolved.insert(key, self.resolve(key).await?);
        }
        Ok(resolved)
    }

    /// Drop cached component resolutions after a reinstall or a Root rotation.
    pub fn refresh_components(&self) {
        self.cache.lock().expect("component cache lock").clear();
    }

    /// The Root's own key list. Read-only; the chain is the authority.
    pub async fn root_keys(&self) -> Result<Vec<String>> {
        let term = wire::root_keys_term(self.manifest.root_uri())?;
        let (value, _meta) = wire::explore_value(&self.inner, &term).await?;
        let values = wire::decode_reply(&value)?;
        let list = values
            .first()
            .and_then(RhoValue::as_list)
            .ok_or_else(|| SdkError::Decode("Root.keys did not reply with a list".into()))?;
        list.iter()
            .map(|item| {
                item.as_str()
                    .map(str::to_string)
                    .ok_or_else(|| SdkError::Decode("Root.keys entry is not a string".into()))
            })
            .collect()
    }

    /// Run a free read and decode the `(true, ...)` envelope.
    pub async fn read(
        &self,
        uri: &RegistryUri,
        arm: &str,
        args: &[String],
    ) -> Result<Read<serde_json::Value>> {
        let term = wire::call_term(uri, arm, args)?;
        let (value, meta) = wire::explore_value(&self.inner, &term).await?;
        let values = wire::decode_reply(&value)?;
        Ok(Read {
            value: models::values_json(&values),
            meta,
        })
    }

    /// Run a signed call and wait for finality. A refusal is returned as data, with its
    /// receipt, because some refusals still change state.
    pub async fn write(
        &self,
        uri: &RegistryUri,
        arm: &str,
        args: &[String],
        with_deployer: bool,
    ) -> Result<WriteOutcome<serde_json::Value>> {
        // The signed template always binds `rho:rchain:deployerId`; `with_deployer` only
        // documents whether the arm itself takes `*deployerId` in `args`.
        let _ = with_deployer;
        let term = wire::call_term_signed(uri, arm, args)?;
        self.write_term(&term).await
    }

    /// Submit a fully-built signed term.
    pub async fn write_term(&self, term: &str) -> Result<WriteOutcome<serde_json::Value>> {
        let receipt = wire::deploy_receipt(&self.inner, term).await?;
        let reply = receipt.reply.clone().ok_or_else(|| SdkError::NoReply {
            deploy_id: receipt.deploy_id.clone(),
            block_number: receipt.block_number,
        })?;
        match wire::decode_reply(&reply) {
            Ok(values) => Ok(WriteOutcome::Accepted(Write {
                value: models::values_json(&values),
                receipt,
            })),
            Err(SdkError::Refused { reason, code }) => Ok(WriteOutcome::Refused {
                reason,
                code,
                receipt,
            }),
            Err(error) => Err(error),
        }
    }

    /// Deploy a raw term and return its receipt. Native-only op-cache support is in
    /// `write_term_cached`.
    pub async fn deploy_term(&self, term: &str) -> Result<DeployReceipt> {
        wire::deploy_receipt(&self.inner, term).await
    }

    /// Native-only: reuse a write-ahead signed body under an operation id.
    #[cfg(not(target_arch = "wasm32"))]
    pub async fn deploy_term_cached(
        &self,
        term: &str,
        op: &str,
        cache_dir: &std::path::Path,
    ) -> Result<DeployReceipt> {
        let outcome = self.inner.deploy_term_cached(term, op, cache_dir).await?;
        receipt_from_outcome(term, outcome)
    }

    /// Change the phlo limit for one deploy. Returns the previous limit.
    pub fn set_phlo_limit(&mut self, limit: i64) -> i64 {
        let previous = self.phlo_limit;
        self.phlo_limit = limit;
        self.inner
            .set_network(self.shard.clone(), limit, self.phlo_price);
        previous
    }
}

fn node_client(node: &str, shard: &str) -> Result<NodeClient> {
    let options = PoolOptions {
        discovery: DiscoveryMode::Disabled,
        shard_id: shard.to_string(),
        ..PoolOptions::default()
    };
    Ok(NodeClient::new_with_options(node, options)?)
}

#[cfg(not(target_arch = "wasm32"))]
fn receipt_from_outcome(term: &str, outcome: rcash_sdk::DeployOutcome) -> Result<DeployReceipt> {
    let status_text = outcome.status.status_text();
    let block_hash = outcome.status.block().map(|block| block.block_hash.clone());
    let block_number = outcome
        .status
        .block()
        .map(|block| block.block_number)
        .unwrap_or_default();
    if !outcome.finalized {
        return Err(SdkError::Unknown {
            deploy_id: outcome.deploy_id,
            last: status_text,
        });
    }
    let reply = match &outcome.status {
        DeployStatus::ProcessedWithSuccess { deploy_result, .. } => {
            deploy_result.first().map(RhoValue::decode).transpose()?
        }
        DeployStatus::ProcessedWithError {
            deploy_error,
            block,
        } => {
            return Err(SdkError::DeployFailed {
                error: deploy_error.clone(),
                block_hash: Some(block.block_hash.clone()),
                deploy_id: Some(outcome.deploy_id),
            })
        }
        DeployStatus::NotProcessed { status } => {
            return Err(SdkError::Unknown {
                deploy_id: outcome.deploy_id,
                last: status.clone(),
            })
        }
    };
    Ok(DeployReceipt {
        deploy_id: outcome.deploy_id,
        finalized: true,
        block_hash,
        block_number,
        term_bytes: term.len(),
        status_text,
        reply,
    })
}

/// A convenience for the `(true, uri)` factory replies.
pub fn reply_uri(value: &serde_json::Value) -> Option<&str> {
    value
        .get("uri")
        .and_then(serde_json::Value::as_str)
        .or_else(|| value.as_str())
}
