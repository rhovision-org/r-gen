//! Structural validation for the JSON payloads the browser sends to the contracts.
//!
//! This is deliberately shallow: the contract is the authority. The point is to catch
//! the mistakes a form can make (missing field, impossible deadline, mismatched
//! credential URIs, oversized nest batch) before a signed deploy is built.

use serde_json::Value;

use crate::error::{Result, RgenError};

fn object<'a>(value: &'a Value, label: &str) -> Result<&'a serde_json::Map<String, Value>> {
    value
        .as_object()
        .ok_or_else(|| RgenError::Validation(format!("{label} must be an object")))
}

fn array<'a>(value: &'a Value, label: &str) -> Result<&'a Vec<Value>> {
    value
        .as_array()
        .ok_or_else(|| RgenError::Validation(format!("{label} must be a list")))
}

fn text(value: &Value, key: &str) -> Result<String> {
    value
        .get(key)
        .and_then(Value::as_str)
        .filter(|text| !text.is_empty())
        .map(str::to_string)
        .ok_or_else(|| RgenError::Validation(format!("{key} must be a non-empty string")))
}

fn optional_text(value: &Value, key: &str) -> Result<()> {
    match value.get(key) {
        None | Some(Value::Null) => Ok(()),
        Some(Value::String(_)) => Ok(()),
        Some(_) => Err(RgenError::Validation(format!("{key} must be a string"))),
    }
}

fn int(value: &Value, key: &str) -> Result<i64> {
    value
        .get(key)
        .and_then(Value::as_i64)
        .ok_or_else(|| RgenError::Validation(format!("{key} must be an integer")))
}

fn positive(value: &Value, key: &str) -> Result<i64> {
    let number = int(value, key)?;
    if number < 1 {
        return Err(RgenError::Validation(format!("{key} must be positive")));
    }
    Ok(number)
}

fn hash_field(value: &Value, key: &str) -> Result<()> {
    let hash = text(value, key)?;
    if hash.len() > 256 {
        return Err(RgenError::Validation(format!("{key} is too long")));
    }
    Ok(())
}

fn criteria(value: &Value) -> Result<()> {
    let criteria = object(value, "selectionCriteria")?;
    for key in ["ctype", "discipline", "jurisdiction", "role"] {
        text(&Value::Object(criteria.clone()), key)?;
    }
    let min = criteria
        .get("minLevel")
        .and_then(Value::as_i64)
        .ok_or_else(|| {
            RgenError::Validation("selectionCriteria.minLevel must be an integer".into())
        })?;
    if min < 1 {
        return Err(RgenError::Validation(
            "selectionCriteria.minLevel must be positive".into(),
        ));
    }
    Ok(())
}

fn liability(value: &Value) -> Result<()> {
    let liability = object(value, "liability")?;
    let responsible = liability
        .get("responsible")
        .and_then(Value::as_str)
        .unwrap_or_default();
    if responsible.is_empty() {
        return Err(RgenError::Validation(
            "liability.responsible must be non-empty".into(),
        ));
    }
    let share = liability
        .get("shareBps")
        .and_then(Value::as_i64)
        .ok_or_else(|| RgenError::Validation("liability.shareBps must be an integer".into()))?;
    if !(0..=10_000).contains(&share) {
        return Err(RgenError::Validation(
            "liability.shareBps must be 0..=10000".into(),
        ));
    }
    optional_text(&Value::Object(liability.clone()), "basisHash")?;
    Ok(())
}

fn require_equal(left: &str, right: &str, label: &str) -> Result<()> {
    if left != right {
        return Err(RgenError::Validation(format!(
            "{label} must match the URI argument"
        )));
    }
    Ok(())
}

/// Validate one payload. `kind` is the facade's stable name.
pub fn validate_payload(kind: &str, value: &Value, at_height: i64) -> Result<()> {
    match kind {
        "identity" => {
            let profile = object(value, "profile")?;
            if let Some(handle) = profile.get("handle").and_then(Value::as_str) {
                let valid = !handle.is_empty()
                    && handle.len() <= 64
                    && handle
                        .chars()
                        .all(|c| c.is_ascii_alphanumeric() || "-_.:".contains(c));
                if !valid {
                    return Err(RgenError::Validation(
                        "handle must be 1..=64 ASCII letters, digits or -_.:".into(),
                    ));
                }
            }
            for key in ["displayNameHash", "orgHash", "contactHash"] {
                optional_text(value, key)?;
            }
            Ok(())
        }
        "identityPatch" => {
            for key in ["displayNameHash", "orgHash", "contactHash"] {
                optional_text(value, key)?;
            }
            Ok(())
        }
        "credential" => {
            for key in ["subject", "ctype", "discipline", "jurisdiction", "role"] {
                text(value, key)?;
            }
            positive(value, "level")?;
            optional_text(value, "evidenceHash")?;
            optional_text(value, "issuerUri")?;
            let expires = value.get("expiresAt").and_then(Value::as_i64).unwrap_or(0);
            if expires < 0 {
                return Err(RgenError::Validation("expiresAt must be >= 0".into()));
            }
            Ok(())
        }
        "claim" => {
            let work = object(value.get("work").unwrap_or(&Value::Null), "work")?;
            text(&Value::Object(work.clone()), "discipline")?;
            text(&Value::Object(work.clone()), "jurisdiction")?;
            optional_text(value, "statementHash")?;
            hash_field(value, "statementHash")?;
            hash_field(value, "definitionHash")?;
            criteria(value.get("selectionCriteria").unwrap_or(&Value::Null))?;
            let quantity = object(value.get("quantity").unwrap_or(&Value::Null), "quantity")?;
            text(&Value::Object(quantity.clone()), "unit")?;
            let amount = quantity
                .get("value")
                .and_then(Value::as_i64)
                .ok_or_else(|| RgenError::Validation("quantity.value must be an integer".into()))?;
            if amount < 0 {
                return Err(RgenError::Validation("quantity.value must be >= 0".into()));
            }
            let deadline = positive(value, "deadlineHeight")?;
            if deadline <= at_height {
                return Err(RgenError::Validation(
                    "deadlineHeight must be greater than the current height".into(),
                ));
            }
            if let Some(comment) = value.get("commentUntilHeight").and_then(Value::as_i64) {
                if comment > deadline {
                    return Err(RgenError::Validation(
                        "commentUntilHeight must not exceed deadlineHeight".into(),
                    ));
                }
            }
            if let Some(reference) = value.get("valuePropositionRef") {
                if !reference.is_null() {
                    object(reference, "valuePropositionRef")?;
                }
            }
            Ok(())
        }
        "validation" => {
            let verdict = text(value, "verdict")?;
            if !matches!(verdict.as_str(), "valid" | "partial" | "invalid") {
                return Err(RgenError::Validation(
                    "verdict must be valid, partial or invalid".into(),
                ));
            }
            let quality = object(value.get("quality").unwrap_or(&Value::Null), "quality")?;
            for key in ["completeness", "correctness", "traceability", "fitness"] {
                let score = quality.get(key).and_then(Value::as_i64).ok_or_else(|| {
                    RgenError::Validation(format!("quality.{key} must be an integer"))
                })?;
                if !(1..=5).contains(&score) {
                    return Err(RgenError::Validation(format!(
                        "quality.{key} must be 1..=5"
                    )));
                }
            }
            text(value, "credentialUri")?;
            optional_text(value, "characteristicsHash")?;
            optional_text(value, "commentHash")?;
            if let Some(evidence) = value.get("evidence") {
                array(evidence, "evidence")?;
            }
            Ok(())
        }
        "approval" => {
            let decision = text(value, "decision")?;
            if !matches!(decision.as_str(), "approve" | "reject") {
                return Err(RgenError::Validation(
                    "decision must be approve or reject".into(),
                ));
            }
            text(value, "credentialUri")?;
            optional_text(value, "conditionsHash")?;
            liability(value.get("liability").unwrap_or(&Value::Null))
        }
        "vp" => {
            object(
                value.get("subjectRef").unwrap_or(&Value::Null),
                "subjectRef",
            )?;
            hash_field(value, "statementHash")?;
            hash_field(value, "termsHash")?;
            criteria(value.get("selectionCriteria").unwrap_or(&Value::Null))?;
            if let Some(beneficiaries) = value.get("beneficiaries") {
                for beneficiary in array(beneficiaries, "beneficiaries")? {
                    if beneficiary.as_str().map(str::is_empty).unwrap_or(true) {
                        return Err(RgenError::Validation(
                            "beneficiaries must be non-empty strings".into(),
                        ));
                    }
                }
            }
            let deadline = positive(value, "deadlineHeight")?;
            if deadline <= at_height {
                return Err(RgenError::Validation(
                    "deadlineHeight must be greater than the current height".into(),
                ));
            }
            Ok(())
        }
        "vpValidation" => {
            text(value, "credentialUri")?;
            optional_text(value, "notesHash")?;
            Ok(())
        }
        "case" => {
            let kind = text(value, "kind")?;
            if kind != "dispute" {
                return Err(RgenError::Validation("kind must be dispute".into()));
            }
            hash_field(value, "groundsHash")?;
            text(value, "adjudicator")?;
            text(value, "adjudicatorCredentialUri")?;
            let deadline = positive(value, "deadlineHeight")?;
            if deadline <= at_height {
                return Err(RgenError::Validation(
                    "deadlineHeight must be greater than the current height".into(),
                ));
            }
            Ok(())
        }
        "decision" => {
            let outcome = text(value, "outcome")?;
            if !matches!(outcome.as_str(), "uphold" | "revoke" | "partial") {
                return Err(RgenError::Validation(
                    "outcome must be uphold, revoke or partial".into(),
                ));
            }
            optional_text(value, "rationaleHash")?;
            optional_text(value, "conditionsHash")?;
            if let Some(liability_value) = value.get("liability") {
                if !liability_value.is_null() {
                    liability(liability_value)?;
                }
            }
            Ok(())
        }
        "evidence" | "comment" | "anchor" => {
            if kind == "anchor" {
                text(value, "kind")?;
                optional_text(value, "parentHash")?;
            }
            hash_field(value, "hash")
        }
        "provenanceCreate" => {
            let asset_ref = value
                .get("assetRef")
                .ok_or_else(|| RgenError::Validation("assetRef is required".into()))?;
            object(asset_ref, "assetRef")?;
            text(asset_ref, "uri")?;
            let writers = array(
                value
                    .get("writers")
                    .ok_or_else(|| RgenError::Validation("writers is required".into()))?,
                "writers",
            )?;
            if writers.is_empty() {
                return Err(RgenError::Validation("writers must not be empty".into()));
            }
            let mut seen = std::collections::BTreeSet::new();
            for writer in writers {
                let writer = writer
                    .as_str()
                    .filter(|writer| !writer.is_empty())
                    .ok_or_else(|| RgenError::Validation("writers must be strings".into()))?;
                if !seen.insert(writer) {
                    return Err(RgenError::Validation("writers must be unique".into()));
                }
            }
            Ok(())
        }
        "childRefs" => {
            let children = array(value, "childRefs")?;
            if children.len() > 32 {
                return Err(RgenError::Validation(
                    "a nest batch is capped at 32 children".into(),
                ));
            }
            for child in children {
                object(child, "child")?;
                text(child, "id")?;
                text(child, "uri")?;
            }
            Ok(())
        }
        "expires" => {
            let expires = int(value, "expiresAt")?;
            if expires < 0 {
                return Err(RgenError::Validation("expiresAt must be >= 0".into()));
            }
            Ok(())
        }
        other => Err(RgenError::Validation(format!(
            "unknown payload kind: {other}"
        ))),
    }
}

/// Validate that a validation/approval map names the same credential as the arm argument.
pub fn require_credential(argument: &str, payload: &Value) -> Result<()> {
    let named = text(payload, "credentialUri")?;
    require_equal(argument, &named, "credentialUri")
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn claim() -> Value {
        json!({
            "work": {"titleHash": "t", "discipline": "structural",
                     "jurisdiction": "US-TX", "projectRef": "p"},
            "selectionCriteria": {"ctype": "Validator", "discipline": "structural",
                                  "jurisdiction": "US-TX", "role": "validator", "minLevel": 1},
            "selectionCriteriaHash": "s",
            "statementHash": "s",
            "definitionHash": "d",
            "quantity": {"unit": "inspections", "value": 12},
            "evidence": [],
            "valuePropositionRef": null,
            "deadlineHeight": 120,
            "commentUntilHeight": 100
        })
    }

    #[test]
    fn accepts_a_well_formed_claim() {
        validate_payload("claim", &claim(), 100).unwrap();
    }

    #[test]
    fn refuses_a_past_deadline_and_a_late_comment_window() {
        let mut past = claim();
        past["deadlineHeight"] = json!(100);
        assert!(validate_payload("claim", &past, 100).is_err());
        let mut late = claim();
        late["commentUntilHeight"] = json!(121);
        assert!(validate_payload("claim", &late, 100).is_err());
    }

    #[test]
    fn refuses_unknown_verdicts_and_mismatched_credentials() {
        let validation = json!({
            "verdict": "maybe",
            "quality": {"completeness": 5, "correctness": 5,
                        "traceability": 5, "fitness": 5},
            "credentialUri": "rho:id:a"
        });
        assert!(validate_payload("validation", &validation, 1).is_err());
        let valid = json!({
            "verdict": "valid",
            "quality": {"completeness": 5, "correctness": 5,
                        "traceability": 5, "fitness": 5},
            "credentialUri": "rho:id:a"
        });
        validate_payload("validation", &valid, 1).unwrap();
        assert!(require_credential("rho:id:a", &valid).is_ok());
        assert!(require_credential("rho:id:b", &valid).is_err());
    }

    #[test]
    fn caps_nest_batches_and_requires_writers() {
        let children: Vec<_> = (0..33)
            .map(|index| json!({"id": format!("rho:id:{index}"), "uri": format!("rho:id:{index}")}))
            .collect();
        assert!(validate_payload("childRefs", &json!(children), 1).is_err());
        let provenance = json!({"assetRef": {"uri": "rho:id:a"}, "writers": []});
        assert!(validate_payload("provenanceCreate", &provenance, 1).is_err());
    }
}
