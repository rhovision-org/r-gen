//! SDK errors and refusal classification.

use rcash_chain::ChainError;

use rgen_core::RgenError;

/// The r-gen refusal vocabulary, grouped for the UI. The contract string is always kept.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum RefusalCode {
    NotOwner,
    NotParty,
    NotOpen,
    NotValidated,
    NotApproved,
    NotDecided,
    Conflict,
    Expired,
    Deadline,
    Height,
    Proof,
    Credential,
    Scope,
    Issuer,
    Revoked,
    Duplicate,
    Fields,
    Unknown,
    Other(String),
}

impl RefusalCode {
    pub fn classify(reason: &str) -> Self {
        match reason {
            "not owner" | "not claimant" | "not proposer" | "not subject" | "not adjudicator"
            | "not writer" => Self::NotOwner,
            "not a party" | "conflict" => Self::NotParty,
            "not open" | "not proposed" | "not validating" => Self::NotOpen,
            "not validated" | "not conditional" => Self::NotValidated,
            "not approved" | "parent not approved or limit" => Self::NotApproved,
            "not decided" | "not finished" | "not executed" => Self::NotDecided,
            "already disputed" | "already revoked" | "already attested" | "already executed"
            | "already applied" => Self::Conflict,
            "expired" | "not expired" => Self::Expired,
            "deadline" | "comment closed" | "clock" => Self::Deadline,
            "height" => Self::Height,
            "proof" | "proof used" | "child proof" | "not qualified" => Self::Proof,
            "forged credential" | "credential" | "self issue" | "self validation" => {
                Self::Credential
            }
            "scope" | "scope mismatch" => Self::Scope,
            "issuer" | "issuer revoked" | "issuer expired" | "issuer scope" | "not issuer" => {
                Self::Issuer
            }
            "revoked" | "not active" => Self::Revoked,
            "duplicate" | "duplicate child" | "order" => Self::Duplicate,
            "fields" | "writers or asset" | "bad version" => Self::Fields,
            "unknown"
            | "unknown child"
            | "unknown claim"
            | "unknown credential"
            | "unknown value proposition"
            | "unknown component" => Self::Unknown,
            other => Self::Other(other.to_string()),
        }
    }
}

/// An SDK error.
#[derive(Debug, thiserror::Error)]
pub enum SdkError {
    #[error(transparent)]
    Chain(#[from] ChainError),
    #[error(transparent)]
    Core(#[from] RgenError),
    #[error("decode error: {0}")]
    Decode(String),
    #[error("refused: {reason}")]
    Refused { reason: String, code: RefusalCode },
    #[error("deploy failed: {error}")]
    DeployFailed {
        error: String,
        block_hash: Option<String>,
        deploy_id: Option<String>,
    },
    #[error("deploy {deploy_id} did not settle: {last}")]
    Unknown { deploy_id: String, last: String },
    #[error("deploy {deploy_id} produced no reply at block {block_number}")]
    NoReply {
        deploy_id: String,
        block_number: i64,
    },
    #[error("wallet is locked")]
    NoKey,
    #[error("term is {bytes} bytes; the budget is {budget}")]
    TermTooLarge { bytes: usize, budget: usize },
    #[error("validation: {0}")]
    Validation(String),
}

impl SdkError {
    pub fn refused(reason: impl Into<String>) -> Self {
        let reason = reason.into();
        let code = RefusalCode::classify(&reason);
        Self::Refused { reason, code }
    }

    /// The deploy id attached to an error, when the deploy was submitted.
    pub fn deploy_id(&self) -> Option<&str> {
        match self {
            SdkError::DeployFailed { deploy_id, .. } => deploy_id.as_deref(),
            SdkError::Unknown { deploy_id, .. } | SdkError::NoReply { deploy_id, .. } => {
                Some(deploy_id)
            }
            _ => None,
        }
    }
}

impl From<rcash_core::CoreError> for SdkError {
    fn from(error: rcash_core::CoreError) -> Self {
        SdkError::Core(RgenError::Core(error))
    }
}

/// The SDK result type.
pub type Result<T> = std::result::Result<T, SdkError>;
