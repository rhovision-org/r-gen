use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Quantity {
    pub unit: String,
    pub value: i64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Credential {
    pub id: String,
    pub subject: String,
    pub issuer: String,
    pub ctype: String,
    pub discipline: String,
    pub jurisdiction: String,
    pub role: String,
    pub level: u8,
    pub evidence_hash: String,
    pub issued_at: i64,
    pub expires_at: i64,
    pub status: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Claim {
    pub id: String,
    pub work_id: String,
    pub claimant: String,
    pub ctype: String,
    pub statement_hash: String,
    pub definition_hash: String,
    pub quantity: Quantity,
    pub status: String,
    pub validation_id: Option<String>,
    pub kasset_id: Option<String>,
    pub approval_id: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct KAsset {
    pub id: String,
    pub claim_id: String,
    pub validation_id: String,
    pub claimant: String,
    pub validator: String,
    pub approver: Option<String>,
    pub status: String,
    pub quality_score: u8,
    pub parent_ids: Vec<String>,
    pub child_ids: Vec<String>,
    pub approval_id: Option<String>,
    pub risk_id: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RiskAssessment {
    pub id: String,
    pub subject_id: String,
    pub severity: u8,
    pub probability: u8,
    pub exposure: u8,
    pub score: u16,
    pub class: String,
    pub insurable: bool,
    pub missing: Vec<String>,
    pub status: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Reputation {
    pub subject: String,
    pub earned: u64,
    pub gross: u64,
    pub weight_bps: u16,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Hold {
    pub id: String,
    pub case_id: String,
    pub asset: String,
    pub amount: u64,
    pub payer: String,
    pub status: String,
}
