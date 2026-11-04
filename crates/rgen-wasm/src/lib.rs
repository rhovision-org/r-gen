//! WASM facade for the r-gen browser wallet and UI.
//!
//! The private key lives only in this module. JS receives encrypted keystore JSON,
//! public identifiers and JSON operation results — never a secret.

use std::fmt::Display;

use rcash_chain::address::eth_address_from_public_key;
use rcash_chain::KeyPair;
use rgen_core::requests::validate_payload;
use rgen_core::{ComponentKey, Manifest};
use rgen_sdk::client::{Write, WriteOutcome};
use rgen_sdk::{Client, DeployReceipt, ReadMeta, ReadSource, SdkError};
use serde_json::{json, Value};
use wasm_bindgen::prelude::*;

/// The crate version.
#[wasm_bindgen]
pub fn version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

/// A connected wallet and SDK client.
#[wasm_bindgen]
pub struct Rgen {
    node: String,
    manifest: Manifest,
    shard: String,
    phlo_limit: i64,
    phlo_price: i64,
    client: Client,
}

#[wasm_bindgen]
impl Rgen {
    /// Create a reader client. Call `unlock` or `create_wallet` to sign.
    #[wasm_bindgen(constructor)]
    pub fn new(node: &str, manifest_json: &str) -> Result<Rgen, JsValue> {
        let manifest = Manifest::from_json(manifest_json).map_err(js)?;
        let client = Client::reader(node, manifest.clone()).map_err(js)?;
        Ok(Self {
            node: node.to_string(),
            manifest,
            shard: Client::DEFAULT_SHARD.to_string(),
            phlo_limit: Client::DEFAULT_PHLO_LIMIT,
            phlo_price: Client::DEFAULT_PHLO_PRICE,
            client,
        })
    }

    /// Generate a key, unlock it, and return the encrypted keystore JSON.
    pub fn create_wallet(&mut self, password: &str) -> Result<String, JsValue> {
        let key = KeyPair::generate().map_err(js)?;
        let eth = eth_address_from_public_key(key.public_bytes()).map_err(js)?;
        let document = rgen_keystore::encrypt(key.secret_bytes(), &eth, password).map_err(js)?;
        self.rebuild(key)?;
        Ok(document)
    }

    /// Decrypt a keystore and unlock the wallet. Returns the REV address.
    pub fn unlock(&mut self, document: &str, password: &str) -> Result<String, JsValue> {
        let secret = rgen_keystore::decrypt(document, password).map_err(js)?;
        let key = KeyPair::from_secret_bytes(&secret).map_err(js)?;
        let address = key.rev_address().map_err(js)?;
        self.rebuild(key)?;
        Ok(address)
    }

    /// Drop the key from memory and keep public reads available.
    pub fn lock(&mut self) -> Result<(), JsValue> {
        self.client = Client::reader(&self.node, self.manifest.clone()).map_err(js)?;
        self.client
            .set_network(&self.shard, self.phlo_limit, self.phlo_price);
        Ok(())
    }

    pub fn is_unlocked(&self) -> bool {
        self.client.has_key()
    }

    pub fn address(&self) -> Option<String> {
        self.client.address().ok()
    }

    pub fn public_key(&self) -> Option<String> {
        self.client.key().map(|key| key.public_hex())
    }

    /// Re-encrypt the current key with a (possibly new) password.
    pub fn export_keystore(&self, password: &str) -> Result<String, JsValue> {
        let key = self.client.key().ok_or_else(|| js("wallet is locked"))?;
        let eth = eth_address_from_public_key(key.public_bytes()).map_err(js)?;
        rgen_keystore::encrypt(key.secret_bytes(), &eth, password).map_err(js)
    }

    /// BLAKE2b-256 of a UTF-8 string, hex. Hash free text before it reaches a term.
    pub fn hash_text(&self, text: &str) -> String {
        let digest = rchain_crypto::hash::blake2b256::hash(text.as_bytes());
        digest.iter().map(|byte| format!("{byte:02x}")).collect()
    }

    /// Generate a fresh operation id. JS supplies the timestamp (`Date.now()`).
    pub fn new_op_id(&self, prefix: &str, now_ms: i64) -> Result<String, JsValue> {
        Ok(rgen_sdk::new_op_id(prefix, now_ms)
            .map_err(js)?
            .as_str()
            .to_string())
    }

    pub fn set_network(&mut self, shard: &str, phlo_limit: i64, phlo_price: i64) {
        self.shard = shard.to_string();
        self.phlo_limit = phlo_limit;
        self.phlo_price = phlo_price;
        self.client.set_network(shard, phlo_limit, phlo_price);
    }

    /// Validate a payload before building a term. `kind` matches the SDK's names.
    pub fn validate_payload(
        &self,
        kind: &str,
        json_text: &str,
        at_height: i64,
    ) -> Result<(), JsValue> {
        let value: Value = serde_json::from_str(json_text)
            .map_err(|error| js(format!("payload JSON: {error}")))?;
        validate_payload(kind, &value, at_height).map_err(js)
    }

    pub async fn height(&self) -> Result<String, JsValue> {
        Ok(self.client.height().await.map_err(js)?.to_string())
    }

    pub async fn status(&self) -> Result<String, JsValue> {
        Ok(self.client.status().await.map_err(js)?.to_string())
    }

    pub async fn deploy_status(&self, deploy_id: &str) -> Result<String, JsValue> {
        let status = self.client.deploy_status(deploy_id).await.map_err(js)?;
        Ok(json!({
            "deployId": deploy_id,
            "status": status.status_text(),
            "blockNumber": status.block().map(|block| block.block_number),
            "blockHash": status.block().map(|block| block.block_hash.as_str()),
            "processed": status.is_processed(),
            "success": status.is_success()
        })
        .to_string())
    }

    pub async fn native_rev_balance(&self, address: &str) -> Result<String, JsValue> {
        let read = self.client.native_rev_balance(address).await.map_err(js)?;
        Ok(read_out(json!(read.value), &read.meta))
    }

    pub async fn resolve(&self, key: &str) -> Result<String, JsValue> {
        let key = ComponentKey::parse(key).map_err(js)?;
        let component = self.client.resolve(key).await.map_err(js)?;
        Ok(json!({"uri": component.uri.as_str(), "version": component.version}).to_string())
    }

    pub async fn resolve_all(&self) -> Result<String, JsValue> {
        let resolved = self.client.resolve_all().await.map_err(js)?;
        let mut output = serde_json::Map::new();
        for (key, component) in resolved {
            output.insert(
                key.key().to_string(),
                json!({"uri": component.uri.as_str(), "version": component.version}),
            );
        }
        Ok(Value::Object(output).to_string())
    }

    pub async fn root_keys(&self) -> Result<String, JsValue> {
        let keys = self.client.root_keys().await.map_err(js)?;
        Ok(json!(keys).to_string())
    }

    // ------------------------------------------------------------------ identity

    pub async fn identity_lookup(&self, address: &str) -> Result<String, JsValue> {
        self.read(self.client.identity_lookup(address).await)
    }

    pub async fn identity_get(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.identity_get(uri).await)
    }

    pub async fn identity_count(&self) -> Result<String, JsValue> {
        self.read(self.client.identity_count().await)
    }

    pub async fn identity_create(&self, profile_json: &str) -> Result<String, JsValue> {
        self.write(self.client.identity_create(profile_json).await)
    }

    pub async fn identity_resume(&self) -> Result<String, JsValue> {
        self.write(self.client.identity_resume().await)
    }

    pub async fn identity_update(&self, uri: &str, patch_json: &str) -> Result<String, JsValue> {
        self.write(self.client.identity_update(uri, patch_json).await)
    }

    // --------------------------------------------------------------- credentials

    pub async fn issuer_get(&self) -> Result<String, JsValue> {
        self.read(self.client.issuer_get().await)
    }

    pub async fn issuer_covers(
        &self,
        requirement_json: &str,
        at_height: i64,
    ) -> Result<String, JsValue> {
        self.read(self.client.issuer_covers(requirement_json, at_height).await)
    }

    pub async fn credential_verify(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.credential_verify(uri).await)
    }

    pub async fn credential_count(&self) -> Result<String, JsValue> {
        self.read(self.client.credential_count().await)
    }

    pub async fn credential_get(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.credential_get(uri).await)
    }

    pub async fn credential_check(
        &self,
        uri: &str,
        caller: &str,
        requirement_json: &str,
        at_height: i64,
    ) -> Result<String, JsValue> {
        self.read(
            self.client
                .credential_check(uri, caller, requirement_json, at_height)
                .await,
        )
    }

    pub async fn credential_issue(&self, request_json: &str) -> Result<String, JsValue> {
        self.write(self.client.credential_issue(request_json).await)
    }

    pub async fn credential_revoke(&self, uri: &str, reason: &str) -> Result<String, JsValue> {
        self.write(self.client.credential_revoke(uri, reason).await)
    }

    pub async fn credential_renew(
        &self,
        uri: &str,
        expires_at: i64,
        evidence_hash: &str,
    ) -> Result<String, JsValue> {
        self.write(
            self.client
                .credential_renew(uri, expires_at, evidence_hash)
                .await,
        )
    }

    pub async fn credential_attest(&self, uri: &str, hash: &str) -> Result<String, JsValue> {
        self.write(self.client.credential_attest(uri, hash).await)
    }

    // -------------------------------------------------------------------- claims

    pub async fn claim_verify(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.claim_verify(uri).await)
    }

    pub async fn claim_get(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.claim_get(uri).await)
    }

    pub async fn claim_comments(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.claim_comments(uri).await)
    }

    pub async fn claim_create(&self, request_json: &str) -> Result<String, JsValue> {
        self.write(self.client.claim_create(request_json).await)
    }

    pub async fn claim_comment(&self, uri: &str, comment_json: &str) -> Result<String, JsValue> {
        self.write(self.client.claim_comment(uri, comment_json).await)
    }

    pub async fn claim_withdraw(&self, uri: &str) -> Result<String, JsValue> {
        self.write(self.client.claim_withdraw(uri).await)
    }

    pub async fn claim_expire(&self, uri: &str) -> Result<String, JsValue> {
        self.write(self.client.claim_expire(uri).await)
    }

    pub async fn claim_validate(
        &self,
        uri: &str,
        credential_uri: &str,
        validation_json: &str,
    ) -> Result<String, JsValue> {
        self.write(
            self.client
                .claim_validate(uri, credential_uri, validation_json)
                .await,
        )
    }

    pub async fn claim_resume(&self, uri: &str) -> Result<String, JsValue> {
        self.write(self.client.claim_resume(uri).await)
    }

    // ------------------------------------------------------------------ K-Assets

    pub async fn kasset_get(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.kasset_get(uri).await)
    }

    pub async fn kasset_children(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.kasset_children(uri).await)
    }

    pub async fn kasset_revocation(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.kasset_revocation(uri).await)
    }

    pub async fn kasset_approve(
        &self,
        uri: &str,
        credential_uri: &str,
        approval_json: &str,
    ) -> Result<String, JsValue> {
        self.write(
            self.client
                .kasset_approve(uri, credential_uri, approval_json)
                .await,
        )
    }

    pub async fn kasset_reject(
        &self,
        uri: &str,
        credential_uri: &str,
        approval_json: &str,
    ) -> Result<String, JsValue> {
        self.write(
            self.client
                .kasset_reject(uri, credential_uri, approval_json)
                .await,
        )
    }

    pub async fn kasset_nest(&self, uri: &str, child_refs_json: &str) -> Result<String, JsValue> {
        self.write(self.client.kasset_nest(uri, child_refs_json).await)
    }

    pub async fn kasset_open_dispute(
        &self,
        uri: &str,
        case_req_json: &str,
    ) -> Result<String, JsValue> {
        self.write(self.client.kasset_open_dispute(uri, case_req_json).await)
    }

    // --------------------------------------------------------- value propositions

    pub async fn vp_verify(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.vp_verify(uri).await)
    }

    pub async fn vp_get(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.vp_get(uri).await)
    }

    pub async fn vp_comments(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.vp_comments(uri).await)
    }

    pub async fn vp_revocation(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.vp_revocation(uri).await)
    }

    pub async fn vp_propose(&self, request_json: &str) -> Result<String, JsValue> {
        self.write(self.client.vp_propose(request_json).await)
    }

    pub async fn vp_validate(
        &self,
        uri: &str,
        credential_uri: &str,
        validation_json: &str,
    ) -> Result<String, JsValue> {
        self.write(
            self.client
                .vp_validate(uri, credential_uri, validation_json)
                .await,
        )
    }

    pub async fn vp_comment(&self, uri: &str, comment_json: &str) -> Result<String, JsValue> {
        self.write(self.client.vp_comment(uri, comment_json).await)
    }

    pub async fn vp_withdraw(&self, uri: &str) -> Result<String, JsValue> {
        self.write(self.client.vp_withdraw(uri).await)
    }

    pub async fn vp_open_dispute(&self, uri: &str, case_req_json: &str) -> Result<String, JsValue> {
        self.write(self.client.vp_open_dispute(uri, case_req_json).await)
    }

    // --------------------------------------------------------------------- cases

    pub async fn case_get(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.case_get(uri).await)
    }

    pub async fn case_evidence(&self, uri: &str, evidence_json: &str) -> Result<String, JsValue> {
        self.write(self.client.case_evidence(uri, evidence_json).await)
    }

    pub async fn case_decide(&self, uri: &str, decision_json: &str) -> Result<String, JsValue> {
        self.write(self.client.case_decide(uri, decision_json).await)
    }

    pub async fn case_execute(&self, uri: &str) -> Result<String, JsValue> {
        self.write(self.client.case_execute(uri).await)
    }

    pub async fn case_expire(&self, uri: &str) -> Result<String, JsValue> {
        self.write(self.client.case_expire(uri).await)
    }

    pub async fn case_close(&self, uri: &str) -> Result<String, JsValue> {
        self.write(self.client.case_close(uri).await)
    }

    // ---------------------------------------------------------------- provenance

    pub async fn provenance_get(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.provenance_get(uri).await)
    }

    pub async fn provenance_anchors(&self, uri: &str) -> Result<String, JsValue> {
        self.read(self.client.provenance_anchors(uri).await)
    }

    pub async fn provenance_verify(&self, uri: &str, hash: &str) -> Result<String, JsValue> {
        self.read(self.client.provenance_verify(uri, hash).await)
    }

    pub async fn provenance_create(&self, request_json: &str) -> Result<String, JsValue> {
        self.write(self.client.provenance_create(request_json).await)
    }

    pub async fn provenance_anchor(
        &self,
        uri: &str,
        document_json: &str,
    ) -> Result<String, JsValue> {
        self.write(self.client.provenance_anchor(uri, document_json).await)
    }

    pub async fn provenance_comment(
        &self,
        uri: &str,
        comment_json: &str,
    ) -> Result<String, JsValue> {
        self.write(self.client.provenance_comment(uri, comment_json).await)
    }
}

impl Rgen {
    fn rebuild(&mut self, key: KeyPair) -> Result<(), JsValue> {
        let mut client = Client::new(&self.node, self.manifest.clone(), key).map_err(js)?;
        client.set_network(&self.shard, self.phlo_limit, self.phlo_price);
        self.client = client;
        Ok(())
    }

    fn read(&self, result: Result<rgen_sdk::Read<Value>, SdkError>) -> Result<String, JsValue> {
        match result {
            Ok(read) => Ok(read_out(read.value, &read.meta)),
            Err(error) => Err(js_error(&error)),
        }
    }

    fn write(&self, result: Result<WriteOutcome<Value>, SdkError>) -> Result<String, JsValue> {
        match result {
            Ok(outcome) => Ok(write_out(outcome)),
            Err(error) => Err(js_error(&error)),
        }
    }
}

fn js(error: impl Display) -> JsValue {
    JsValue::from_str(&error.to_string())
}

fn js_error(error: &SdkError) -> JsValue {
    let (code, deploy_id) = match error {
        SdkError::Refused { .. } => ("refused", None),
        SdkError::DeployFailed { deploy_id, .. } => ("deploy", deploy_id.clone()),
        SdkError::Unknown { deploy_id, .. } => ("unknown", Some(deploy_id.clone())),
        SdkError::NoReply { deploy_id, .. } => ("unknown", Some(deploy_id.clone())),
        SdkError::Validation(_) => ("validation", None),
        SdkError::Decode(_) => ("decode", None),
        SdkError::Core(_) | SdkError::Chain(_) => ("chain", None),
        SdkError::NoKey => ("locked", None),
        SdkError::TermTooLarge { .. } => ("term", None),
    };
    JsValue::from_str(
        &json!({
            "ok": false,
            "code": code,
            "message": error.to_string(),
            "deployId": deploy_id
        })
        .to_string(),
    )
}

fn read_out(data: Value, meta: &ReadMeta) -> String {
    json!({
        "ok": true,
        "data": data,
        "read": {
            "atHeight": meta.at_height,
            "blockHash": meta.block_hash,
            "source": match meta.source {
                ReadSource::Explore => "explore",
                ReadSource::SignedDeploy => "signedDeploy",
            },
            "deployId": meta.deploy_id
        }
    })
    .to_string()
}

fn write_out(outcome: WriteOutcome<Value>) -> String {
    match outcome {
        WriteOutcome::Accepted(Write { value, receipt }) => json!({
            "ok": true,
            "data": value,
            "deploy": receipt_json(&receipt)
        })
        .to_string(),
        WriteOutcome::Refused {
            reason,
            code,
            receipt,
        } => json!({
            "ok": false,
            "code": "refused",
            "refusal": format!("{code:?}").to_lowercase(),
            "message": reason,
            "deploy": receipt_json(&receipt)
        })
        .to_string(),
    }
}

fn receipt_json(receipt: &DeployReceipt) -> Value {
    json!({
        "deployId": receipt.deploy_id,
        "finalized": receipt.finalized,
        "blockHash": receipt.block_hash,
        "blockNumber": receipt.block_number,
        "termBytes": receipt.term_bytes,
        "status": receipt.status_text
    })
}
