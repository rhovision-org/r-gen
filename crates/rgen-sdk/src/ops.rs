//! Typed protocol operations.
//!
//! Every method maps to one arm on the installed contracts. Read methods use free
//! `explore-deploy`; write methods sign and wait for finality. Payloads are validated
//! structurally before they are rendered.

use rcash_chain::rho_expr::RhoValue;
use rgen_core::render::{quote_string, render_json};
use rgen_core::requests::{require_credential, validate_payload};
use rgen_core::{ComponentKey, RegistryUri};
use serde_json::Value;

use crate::client::{Client, WriteOutcome};
use crate::error::{Result, SdkError};
use crate::wire::{Read, ReadMeta, ReadSource};

fn uri(value: &str) -> Result<RegistryUri> {
    Ok(RegistryUri::new(value)?)
}

fn quoted(value: &str) -> Result<String> {
    Ok(quote_string(value)?)
}

fn parse(value: &str, label: &str) -> Result<Value> {
    serde_json::from_str(value)
        .map_err(|error| SdkError::Validation(format!("{label} JSON: {error}")))
}

fn rendered(value: &Value) -> Result<String> {
    Ok(render_json(value)?)
}

fn check(kind: &str, value: &Value, at_height: i64) -> Result<()> {
    validate_payload(kind, value, at_height)
        .map_err(|error| SdkError::Validation(error.to_string()))
}

impl Client {
    async fn read_component(
        &self,
        key: ComponentKey,
        arm: &str,
        args: &[String],
    ) -> Result<Read<Value>> {
        let component = self.resolve(key).await?;
        self.read(&component.uri, arm, args).await
    }

    async fn write_component(
        &self,
        key: ComponentKey,
        arm: &str,
        args: &[String],
    ) -> Result<WriteOutcome<Value>> {
        let component = self.resolve(key).await?;
        self.write(&component.uri, arm, args, true).await
    }

    async fn write_entity(
        &self,
        value: &str,
        arm: &str,
        args: &[String],
        with_deployer: bool,
    ) -> Result<WriteOutcome<Value>> {
        self.write(&uri(value)?, arm, args, with_deployer).await
    }

    // ---------------------------------------------------------------- identity

    pub async fn identity_lookup(&self, address: &str) -> Result<Read<Value>> {
        self.read_component(
            ComponentKey::IdentityDirectory,
            "lookup",
            &[quoted(address)?],
        )
        .await
    }

    pub async fn identity_count(&self) -> Result<Read<Value>> {
        self.read_component(ComponentKey::IdentityDirectory, "count", &[])
            .await
    }

    pub async fn identity_get(&self, entity: &str) -> Result<Read<Value>> {
        self.read(&uri(entity)?, "get", &[]).await
    }

    pub async fn identity_create(&self, profile_json: &str) -> Result<WriteOutcome<Value>> {
        let profile = parse(profile_json, "profile")?;
        check("identity", &profile, 0)?;
        self.write_component(
            ComponentKey::IdentityFactory,
            "create",
            &["*deployerId".into(), rendered(&profile)?],
        )
        .await
    }

    pub async fn identity_resume(&self) -> Result<WriteOutcome<Value>> {
        let subject = self.address()?;
        self.write_component(
            ComponentKey::IdentityFactory,
            "resume",
            &["*deployerId".into(), quoted(&subject)?],
        )
        .await
    }

    pub async fn identity_update(
        &self,
        entity: &str,
        patch_json: &str,
    ) -> Result<WriteOutcome<Value>> {
        let patch = parse(patch_json, "patch")?;
        check("identityPatch", &patch, 0)?;
        self.write_entity(
            entity,
            "update",
            &["*deployerId".into(), rendered(&patch)?],
            true,
        )
        .await
    }

    // ------------------------------------------------------------- credentials

    pub async fn issuer_get(&self) -> Result<Read<Value>> {
        self.read_component(ComponentKey::Issuer, "get", &[]).await
    }

    pub async fn issuer_covers(
        &self,
        requirement_json: &str,
        at_height: i64,
    ) -> Result<Read<Value>> {
        let requirement = parse(requirement_json, "requirement")?;
        self.read_component(
            ComponentKey::Issuer,
            "covers",
            &[rendered(&requirement)?, at_height.to_string()],
        )
        .await
    }

    pub async fn credential_verify(&self, entity: &str) -> Result<Read<Value>> {
        self.read_component(
            ComponentKey::CredentialFactory,
            "verify",
            &[quoted(entity)?],
        )
        .await
    }

    pub async fn credential_count(&self) -> Result<Read<Value>> {
        self.read_component(ComponentKey::CredentialFactory, "count", &[])
            .await
    }

    pub async fn credential_get(&self, entity: &str) -> Result<Read<Value>> {
        self.read(&uri(entity)?, "get", &[]).await
    }

    pub async fn credential_check(
        &self,
        entity: &str,
        caller: &str,
        requirement_json: &str,
        at_height: i64,
    ) -> Result<Read<Value>> {
        let requirement = parse(requirement_json, "requirement")?;
        self.read(
            &uri(entity)?,
            "check",
            &[
                quoted(caller)?,
                rendered(&requirement)?,
                at_height.to_string(),
            ],
        )
        .await
    }

    pub async fn credential_issue(&self, request_json: &str) -> Result<WriteOutcome<Value>> {
        let request = parse(request_json, "credential")?;
        check("credential", &request, 0)?;
        self.write_component(
            ComponentKey::CredentialFactory,
            "issue",
            &["*deployerId".into(), rendered(&request)?],
        )
        .await
    }

    pub async fn credential_revoke(
        &self,
        entity: &str,
        reason: &str,
    ) -> Result<WriteOutcome<Value>> {
        self.write_entity(
            entity,
            "revoke",
            &["*deployerId".into(), quoted(reason)?],
            true,
        )
        .await
    }

    pub async fn credential_renew(
        &self,
        entity: &str,
        expires_at: i64,
        evidence_hash: &str,
    ) -> Result<WriteOutcome<Value>> {
        if expires_at < 0 {
            return Err(SdkError::Validation("expiresAt must be >= 0".into()));
        }
        self.write_entity(
            entity,
            "renew",
            &[
                "*deployerId".into(),
                expires_at.to_string(),
                quoted(evidence_hash)?,
            ],
            true,
        )
        .await
    }

    pub async fn credential_attest(&self, entity: &str, hash: &str) -> Result<WriteOutcome<Value>> {
        self.write_entity(
            entity,
            "attest",
            &["*deployerId".into(), quoted(hash)?],
            true,
        )
        .await
    }

    // ------------------------------------------------------------------ claims

    pub async fn claim_verify(&self, entity: &str) -> Result<Read<Value>> {
        self.read_component(ComponentKey::ClaimFactory, "verify", &[quoted(entity)?])
            .await
    }

    pub async fn claim_get(&self, entity: &str) -> Result<Read<Value>> {
        self.read(&uri(entity)?, "get", &[]).await
    }

    pub async fn claim_comments(&self, entity: &str) -> Result<Read<Value>> {
        self.read(&uri(entity)?, "comments", &[]).await
    }

    pub async fn claim_create(&self, request_json: &str) -> Result<WriteOutcome<Value>> {
        let request = parse(request_json, "claim")?;
        let height = self.height().await?;
        check("claim", &request, height)?;
        self.write_component(
            ComponentKey::ClaimFactory,
            "create",
            &["*deployerId".into(), rendered(&request)?],
        )
        .await
    }

    pub async fn claim_comment(
        &self,
        entity: &str,
        comment_json: &str,
    ) -> Result<WriteOutcome<Value>> {
        let comment = parse(comment_json, "comment")?;
        check("comment", &comment, 0)?;
        self.write_entity(
            entity,
            "comment",
            &["*deployerId".into(), rendered(&comment)?],
            true,
        )
        .await
    }

    pub async fn claim_withdraw(&self, entity: &str) -> Result<WriteOutcome<Value>> {
        self.write_entity(entity, "withdraw", &["*deployerId".into()], true)
            .await
    }

    pub async fn claim_expire(&self, entity: &str) -> Result<WriteOutcome<Value>> {
        self.write_entity(entity, "expire", &[], false).await
    }

    pub async fn claim_validate(
        &self,
        entity: &str,
        credential_uri: &str,
        validation_json: &str,
    ) -> Result<WriteOutcome<Value>> {
        let validation = parse(validation_json, "validation")?;
        check("validation", &validation, 0)?;
        require_credential(credential_uri, &validation)
            .map_err(|error| SdkError::Validation(error.to_string()))?;
        self.write_entity(
            entity,
            "validate",
            &[
                "*deployerId".into(),
                quoted(credential_uri)?,
                rendered(&validation)?,
            ],
            true,
        )
        .await
    }

    pub async fn claim_resume(&self, entity: &str) -> Result<WriteOutcome<Value>> {
        self.write_entity(entity, "resume", &["*deployerId".into()], true)
            .await
    }

    // ---------------------------------------------------------------- K-Assets

    pub async fn kasset_get(&self, entity: &str) -> Result<Read<Value>> {
        self.read(&uri(entity)?, "get", &[]).await
    }

    pub async fn kasset_children(&self, entity: &str) -> Result<Read<Value>> {
        self.read(&uri(entity)?, "children", &[]).await
    }

    pub async fn kasset_revocation(&self, entity: &str) -> Result<Read<Value>> {
        self.read(&uri(entity)?, "revocation", &[]).await
    }

    pub async fn kasset_approve(
        &self,
        entity: &str,
        credential_uri: &str,
        approval_json: &str,
    ) -> Result<WriteOutcome<Value>> {
        let approval = parse(approval_json, "approval")?;
        check("approval", &approval, 0)?;
        require_credential(credential_uri, &approval)
            .map_err(|error| SdkError::Validation(error.to_string()))?;
        self.write_entity(
            entity,
            "approve",
            &[
                "*deployerId".into(),
                quoted(credential_uri)?,
                rendered(&approval)?,
            ],
            true,
        )
        .await
    }

    pub async fn kasset_reject(
        &self,
        entity: &str,
        credential_uri: &str,
        approval_json: &str,
    ) -> Result<WriteOutcome<Value>> {
        let approval = parse(approval_json, "approval")?;
        check("approval", &approval, 0)?;
        require_credential(credential_uri, &approval)
            .map_err(|error| SdkError::Validation(error.to_string()))?;
        self.write_entity(
            entity,
            "reject",
            &[
                "*deployerId".into(),
                quoted(credential_uri)?,
                rendered(&approval)?,
            ],
            true,
        )
        .await
    }

    pub async fn kasset_nest(
        &self,
        entity: &str,
        child_refs_json: &str,
    ) -> Result<WriteOutcome<Value>> {
        let children = parse(child_refs_json, "childRefs")?;
        check("childRefs", &children, 0)?;
        self.write_entity(
            entity,
            "nest",
            &["*deployerId".into(), rendered(&children)?],
            true,
        )
        .await
    }

    pub async fn kasset_open_dispute(
        &self,
        entity: &str,
        case_req_json: &str,
    ) -> Result<WriteOutcome<Value>> {
        let case_req = parse(case_req_json, "case")?;
        let height = self.height().await?;
        check("case", &case_req, height)?;
        self.write_entity(
            entity,
            "openDispute",
            &["*deployerId".into(), rendered(&case_req)?],
            true,
        )
        .await
    }

    // ------------------------------------------------------- value propositions

    pub async fn vp_verify(&self, entity: &str) -> Result<Read<Value>> {
        self.read_component(
            ComponentKey::ValuePropositionFactory,
            "verify",
            &[quoted(entity)?],
        )
        .await
    }

    pub async fn vp_get(&self, entity: &str) -> Result<Read<Value>> {
        self.read(&uri(entity)?, "get", &[]).await
    }

    pub async fn vp_comments(&self, entity: &str) -> Result<Read<Value>> {
        self.read(&uri(entity)?, "comments", &[]).await
    }

    pub async fn vp_revocation(&self, entity: &str) -> Result<Read<Value>> {
        self.read(&uri(entity)?, "revocation", &[]).await
    }

    pub async fn vp_propose(&self, request_json: &str) -> Result<WriteOutcome<Value>> {
        let request = parse(request_json, "vp")?;
        let height = self.height().await?;
        check("vp", &request, height)?;
        self.write_component(
            ComponentKey::ValuePropositionFactory,
            "propose",
            &["*deployerId".into(), rendered(&request)?],
        )
        .await
    }

    pub async fn vp_validate(
        &self,
        entity: &str,
        credential_uri: &str,
        validation_json: &str,
    ) -> Result<WriteOutcome<Value>> {
        let validation = parse(validation_json, "vpValidation")?;
        check("vpValidation", &validation, 0)?;
        require_credential(credential_uri, &validation)
            .map_err(|error| SdkError::Validation(error.to_string()))?;
        self.write_entity(
            entity,
            "validate",
            &[
                "*deployerId".into(),
                quoted(credential_uri)?,
                rendered(&validation)?,
            ],
            true,
        )
        .await
    }

    pub async fn vp_comment(
        &self,
        entity: &str,
        comment_json: &str,
    ) -> Result<WriteOutcome<Value>> {
        let comment = parse(comment_json, "comment")?;
        check("comment", &comment, 0)?;
        self.write_entity(
            entity,
            "comment",
            &["*deployerId".into(), rendered(&comment)?],
            true,
        )
        .await
    }

    pub async fn vp_withdraw(&self, entity: &str) -> Result<WriteOutcome<Value>> {
        self.write_entity(entity, "withdraw", &["*deployerId".into()], true)
            .await
    }

    pub async fn vp_open_dispute(
        &self,
        entity: &str,
        case_req_json: &str,
    ) -> Result<WriteOutcome<Value>> {
        let case_req = parse(case_req_json, "case")?;
        let height = self.height().await?;
        check("case", &case_req, height)?;
        self.write_entity(
            entity,
            "openDispute",
            &["*deployerId".into(), rendered(&case_req)?],
            true,
        )
        .await
    }

    // ------------------------------------------------------------------- cases

    pub async fn case_get(&self, entity: &str) -> Result<Read<Value>> {
        self.read(&uri(entity)?, "get", &[]).await
    }

    pub async fn case_evidence(
        &self,
        entity: &str,
        evidence_json: &str,
    ) -> Result<WriteOutcome<Value>> {
        let evidence = parse(evidence_json, "evidence")?;
        check("evidence", &evidence, 0)?;
        self.write_entity(
            entity,
            "evidence",
            &["*deployerId".into(), rendered(&evidence)?],
            true,
        )
        .await
    }

    pub async fn case_decide(
        &self,
        entity: &str,
        decision_json: &str,
    ) -> Result<WriteOutcome<Value>> {
        let decision = parse(decision_json, "decision")?;
        check("decision", &decision, 0)?;
        self.write_entity(
            entity,
            "decide",
            &["*deployerId".into(), rendered(&decision)?],
            true,
        )
        .await
    }

    pub async fn case_execute(&self, entity: &str) -> Result<WriteOutcome<Value>> {
        self.write_entity(entity, "execute", &[], false).await
    }

    pub async fn case_expire(&self, entity: &str) -> Result<WriteOutcome<Value>> {
        self.write_entity(entity, "expire", &[], false).await
    }

    pub async fn case_close(&self, entity: &str) -> Result<WriteOutcome<Value>> {
        self.write_entity(entity, "close", &[], false).await
    }

    // -------------------------------------------------------------- provenance

    pub async fn provenance_get(&self, entity: &str) -> Result<Read<Value>> {
        self.read(&uri(entity)?, "get", &[]).await
    }

    pub async fn provenance_anchors(&self, entity: &str) -> Result<Read<Value>> {
        self.read(&uri(entity)?, "anchors", &[]).await
    }

    pub async fn provenance_verify(&self, entity: &str, hash: &str) -> Result<Read<Value>> {
        self.read(&uri(entity)?, "verify", &[quoted(hash)?]).await
    }

    pub async fn provenance_create(&self, request_json: &str) -> Result<WriteOutcome<Value>> {
        let request = parse(request_json, "provenanceCreate")?;
        check("provenanceCreate", &request, 0)?;
        let asset_ref = request
            .get("assetRef")
            .cloned()
            .ok_or_else(|| SdkError::Validation("assetRef is required".into()))?;
        let writers = request
            .get("writers")
            .cloned()
            .ok_or_else(|| SdkError::Validation("writers is required".into()))?;
        self.write_component(
            ComponentKey::ProvenanceFactory,
            "create",
            &[
                "*deployerId".into(),
                rendered(&asset_ref)?,
                rendered(&writers)?,
            ],
        )
        .await
    }

    pub async fn provenance_anchor(
        &self,
        entity: &str,
        document_json: &str,
    ) -> Result<WriteOutcome<Value>> {
        let document = parse(document_json, "anchor")?;
        check("anchor", &document, 0)?;
        self.write_entity(
            entity,
            "anchor",
            &["*deployerId".into(), rendered(&document)?],
            true,
        )
        .await
    }

    pub async fn provenance_comment(
        &self,
        entity: &str,
        comment_json: &str,
    ) -> Result<WriteOutcome<Value>> {
        let comment = parse(comment_json, "comment")?;
        check("comment", &comment, 0)?;
        self.write_entity(
            entity,
            "comment",
            &["*deployerId".into(), rendered(&comment)?],
            true,
        )
        .await
    }
}

/// Read metadata for a locally constructed value (the facade's previews).
pub fn explore_meta(at_height: i64, block_hash: &str) -> ReadMeta {
    ReadMeta {
        at_height,
        block_hash: block_hash.to_string(),
        source: ReadSource::Explore,
        deploy_id: None,
    }
}

/// Unwrap a factory reply `{id, uri}` into its URI.
pub fn factory_uri(value: &Value) -> Option<&str> {
    value.get("uri").and_then(Value::as_str)
}

/// The decoded URI from a read value that is a plain string.
pub fn uri_text(value: &RhoValue) -> Option<&str> {
    value.as_str()
}
