//! Deploy operation identifiers.
//!
//! An op id names one signed intent. The native CLI uses it to reuse a write-ahead
//! signed body on retry; the browser uses it only to label a journal entry. A new intent
//! always gets a new op id.

use std::fmt;

use crate::error::{Result, RgenError};

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct OpId(String);

impl OpId {
    pub fn new(value: impl Into<String>) -> Result<Self> {
        let value = value.into();
        let valid = !value.is_empty()
            && value.len() <= 96
            && value
                .chars()
                .all(|character| character.is_ascii_alphanumeric() || "-_.:".contains(character));
        if valid {
            Ok(Self(value))
        } else {
            Err(RgenError::Id(format!(
                "opId must be 1..=96 ASCII alphanumerics or -_.:, got {value:?}"
            )))
        }
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for OpId {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl std::str::FromStr for OpId {
    type Err = RgenError;

    fn from_str(value: &str) -> std::result::Result<Self, Self::Err> {
        Self::new(value)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_ids() {
        assert!(OpId::new("claim-1700000000000-aabb").is_ok());
        assert!(OpId::new("").is_err());
        assert!(OpId::new("has space").is_err());
        assert!(OpId::new("quote\"").is_err());
        assert!(OpId::new("x".repeat(97)).is_err());
    }
}
