//! Explore/deploy glue and Rholang call templates.
//!
//! A read term replies on the first `new`-bound name because that is what
//! `explore-deploy` captures. A signed term replies on `rho:rchain:deployId`.

use rcash_chain::node::DeployStatus;
use rcash_chain::rho_expr::{Reply, RhoValue};
use rcash_sdk::Client as RcashClient;

use rgen_core::render::{check_project_size, quote_string};
use rgen_core::RegistryUri;

use crate::error::{Result, SdkError};

/// Where a value came from.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ReadSource {
    Explore,
    SignedDeploy,
}

/// Metadata attached to every read.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ReadMeta {
    pub at_height: i64,
    pub block_hash: String,
    pub source: ReadSource,
    pub deploy_id: Option<String>,
}

/// A read value and its provenance.
#[derive(Clone, Debug, PartialEq)]
pub struct Read<T> {
    pub value: T,
    pub meta: ReadMeta,
}

/// A deploy's receipt. A finalized successful deploy is not yet a success: the caller
/// must check the protocol reply.
#[derive(Clone, Debug, PartialEq)]
pub struct DeployReceipt {
    pub deploy_id: String,
    pub finalized: bool,
    pub block_hash: Option<String>,
    pub block_number: i64,
    pub term_bytes: usize,
    pub status_text: String,
    pub reply: Option<RhoValue>,
}

/// Build an explore-term call to a capability.
///
/// `args` are already-rendered Rholang expressions. The template appends the reply
/// channel, so an arm's own `ret` parameter is not included here.
pub fn call_term(uri: &RegistryUri, arm: &str, args: &[String]) -> Result<String> {
    let arm = quote_string(arm)?;
    let args = render_args(args);
    let term = format!(
        "new reply, rl(`rho:registry:lookup`), capabilityCh, resultCh in {{ \
         rl!(`{uri}`, *capabilityCh) | \
         for (capability <- capabilityCh) {{ \
         capability!({arm}{args}, *resultCh) | \
         for (@replyValue <- resultCh) {{ reply!(replyValue) }} }} }}"
    );
    check_project_size(&term)?;
    Ok(term)
}

/// Build a signed call to a capability. The reply goes to `deployId`.
pub fn call_term_signed(uri: &RegistryUri, arm: &str, args: &[String]) -> Result<String> {
    let arm = quote_string(arm)?;
    let args = render_args(args);
    let term = format!(
        "new rl(`rho:registry:lookup`), capabilityCh, resultCh, \
         deployerId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{ \
         rl!(`{uri}`, *capabilityCh) | \
         for (capability <- capabilityCh) {{ \
         capability!({arm}{args}, *resultCh) | \
         for (@replyValue <- resultCh) {{ deployId!(replyValue) }} }} }}"
    );
    check_project_size(&term)?;
    Ok(term)
}

/// Build a signed `ProvenanceFactory.createBound` call. The subject is resolved to a
/// capability and passed as a name, so the factory can bind the record to the subject's
/// own `uri` rather than a caller-supplied asset reference (RGA-022).
pub fn create_bound_term_signed(
    factory: &RegistryUri,
    subject: &RegistryUri,
    writers: &str,
) -> Result<String> {
    let term = format!(
        "new rl(`rho:registry:lookup`), factoryCh, subjectCh, resultCh, \
         deployerId(`rho:rchain:deployerId`), deployId(`rho:rchain:deployId`) in {{ \
         rl!(`{factory}`, *factoryCh) | rl!(`{subject}`, *subjectCh) | \
         for (ProvenanceFactory <- factoryCh; Subject <- subjectCh) {{ \
         ProvenanceFactory!(\"createBound\", *deployerId, *Subject, {writers}, *resultCh) | \
         for (@replyValue <- resultCh) {{ deployId!(replyValue) }} }} }}"
    );
    check_project_size(&term)?;
    Ok(term)
}

/// Build a native REV vault balance read.
pub fn native_rev_balance_term(address: &str) -> Result<String> {
    let address = quote_string(address)?;
    let term = format!(
        "new reply, revVault(`rho:rchain:revVault`), resultCh in {{ \
         revVault!(\"getBalance\", {address}, *resultCh) | \
         for (@balance <- resultCh) {{ reply!(balance) }} }}"
    );
    check_project_size(&term)?;
    Ok(term)
}

/// Build a Root `resolve` read. `GenRoot.resolve` takes `(key, ret)`.
pub fn resolve_term(root: &RegistryUri, key: &str) -> Result<String> {
    call_term(root, "resolve", &[quote_string(key)?])
}

/// Build a Root `keys` read.
pub fn root_keys_term(root: &RegistryUri) -> Result<String> {
    call_term(root, "keys", &[])
}

fn render_args(args: &[String]) -> String {
    if args.is_empty() {
        String::new()
    } else {
        format!(", {}", args.join(", "))
    }
}

/// Run a public read and decode its value.
pub async fn explore_value(client: &RcashClient, term: &str) -> Result<(RhoValue, ReadMeta)> {
    let response = client.node().explore(term).await?;
    let first = response.expr.first().ok_or_else(|| {
        SdkError::Decode(
            "explore-deploy returned no value; the URI may not exist on this chain (stale manifest?)"
                .into(),
        )
    })?;
    let value = RhoValue::decode(first)?;
    Ok((
        value,
        ReadMeta {
            at_height: response.block.block_number,
            block_hash: response.block.block_hash,
            source: ReadSource::Explore,
            deploy_id: None,
        },
    ))
}

/// Sign, submit and wait for a deploy. Returns the receipt even when it carries no reply.
pub async fn deploy_receipt(client: &RcashClient, term: &str) -> Result<DeployReceipt> {
    check_project_size(term)?;
    let outcome = client.deploy_term(term).await?;
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

/// Decode the protocol `(true, ...)` / `(false, reason)` convention.
pub fn decode_reply(value: &RhoValue) -> Result<Vec<RhoValue>> {
    match Reply::from_value(value)? {
        Reply::Ok(values) => Ok(values),
        Reply::Refused(reason) => Err(SdkError::refused(reason)),
    }
}

/// Decode a reply that may legitimately be a refusal (for probes and previews).
pub fn decode_reply_or_refusal(
    value: &RhoValue,
) -> Result<std::result::Result<Vec<RhoValue>, String>> {
    match Reply::from_value(value)? {
        Reply::Ok(values) => Ok(Ok(values)),
        Reply::Refused(reason) => Ok(Err(reason)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn uri() -> RegistryUri {
        RegistryUri::new("rho:id:abc123").unwrap()
    }

    #[test]
    fn explore_terms_reply_on_the_first_private_name() {
        let term = call_term(&uri(), "get", &[]).unwrap();
        assert!(term.starts_with("new reply,"));
        assert!(term.contains("capability!(\"get\", *resultCh)"));
        assert!(term.contains("reply!(replyValue)"));
        assert!(!term.contains("deployId"));
    }

    #[test]
    fn signed_terms_reply_on_the_deploy_id() {
        let term = call_term_signed(&uri(), "approve", &["*deployerId".into()]).unwrap();
        assert!(term.contains("deployId(`rho:rchain:deployId`)"));
        assert!(term.contains("deployId!(replyValue)"));
    }

    #[test]
    fn root_resolve_has_the_contract_arity() {
        let term = resolve_term(&uri(), "component:claim-factory").unwrap();
        assert!(term.contains("capability!(\"resolve\", \"component:claim-factory\", *resultCh)"));
    }

    #[test]
    fn root_keys_has_no_arguments() {
        let term = root_keys_term(&uri()).unwrap();
        assert!(term.contains("capability!(\"keys\", *resultCh)"));
    }
}
