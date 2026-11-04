use crate::error::RgenError;

macro_rules! id_type {
    ($name:ident, $prefix:literal) => {
        #[derive(Debug, Clone, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
        #[serde(transparent)]
        pub struct $name(String);

        impl $name {
            pub fn new(value: impl Into<String>) -> Result<Self, RgenError> {
                let value = value.into();
                if !value.starts_with($prefix) || value.len() <= $prefix.len() {
                    return Err(RgenError::Id(value));
                }
                Ok(Self(value))
            }

            pub fn as_str(&self) -> &str {
                &self.0
            }
        }

        impl std::fmt::Display for $name {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                f.write_str(&self.0)
            }
        }
    };
}

id_type!(WorkId, "wk:");
id_type!(ClaimId, "cl:");
id_type!(ValidationId, "vl:");
id_type!(KAssetId, "ka:");
id_type!(ApprovalId, "ap:");
id_type!(CredentialId, "cr:");
id_type!(RiskId, "rk:");
id_type!(SealId, "sl:");
id_type!(AnchorId, "an:");
id_type!(CommentId, "cm:");
id_type!(CaseId, "cs:");
id_type!(HoldId, "hd:");

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ids_require_their_prefix() {
        assert!(ClaimId::new("cl:wk:abc:1").is_ok());
        assert!(ClaimId::new("ka:abc").is_err());
        assert!(ClaimId::new("cl:").is_err());
    }
}
