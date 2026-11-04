use crate::error::RgenError;

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum RiskClass {
    Low,
    Medium,
    High,
    Extreme,
}

impl RiskClass {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Low => "low",
            Self::Medium => "medium",
            Self::High => "high",
            Self::Extreme => "extreme",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RiskGates {
    pub validator_level: u8,
    pub approver_level: u8,
    pub needs_oracle: bool,
}

/// `score = severity * probability * exposure`, each factor bounded so the score is 1..100.
pub fn risk_score(severity: u8, probability: u8, exposure: u8) -> Result<u16, RgenError> {
    if !(1..=5).contains(&severity) {
        return Err(RgenError::FactorRange("severity"));
    }
    if !(1..=5).contains(&probability) {
        return Err(RgenError::FactorRange("probability"));
    }
    if !(1..=4).contains(&exposure) {
        return Err(RgenError::FactorRange("exposure"));
    }
    Ok(u16::from(severity) * u16::from(probability) * u16::from(exposure))
}

pub fn risk_class(score: u16) -> Result<RiskClass, RgenError> {
    match score {
        1..=20 => Ok(RiskClass::Low),
        21..=45 => Ok(RiskClass::Medium),
        46..=70 => Ok(RiskClass::High),
        71..=100 => Ok(RiskClass::Extreme),
        _ => Err(RgenError::FactorRange("score")),
    }
}

pub fn risk_gates(class: RiskClass) -> RiskGates {
    match class {
        RiskClass::Low => RiskGates {
            validator_level: 1,
            approver_level: 1,
            needs_oracle: false,
        },
        RiskClass::Medium => RiskGates {
            validator_level: 2,
            approver_level: 2,
            needs_oracle: false,
        },
        RiskClass::High => RiskGates {
            validator_level: 2,
            approver_level: 3,
            needs_oracle: false,
        },
        RiskClass::Extreme => RiskGates {
            validator_level: 3,
            approver_level: 3,
            needs_oracle: true,
        },
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct TriTest {
    pub insurable: bool,
    pub missing: Vec<&'static str>,
}

pub fn tri_test(
    exposure_ref: &str,
    probability_basis: &str,
    consequence_basis: &str,
    consequence_ref: &str,
) -> TriTest {
    let mut missing = Vec::new();
    if exposure_ref.trim().is_empty() {
        missing.push("exposureRef");
    }
    if probability_basis.trim().is_empty() {
        missing.push("probabilityBasis");
    }
    if consequence_basis.trim().is_empty() {
        missing.push("consequenceBasis");
    }
    if consequence_ref.trim().is_empty() {
        missing.push("consequenceRef");
    }
    TriTest {
        insurable: missing.is_empty(),
        missing,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn scores_and_classes() {
        assert_eq!(risk_score(1, 1, 1), Ok(1));
        assert_eq!(risk_score(4, 3, 3), Ok(36));
        assert_eq!(risk_score(5, 5, 4), Ok(100));
        assert_eq!(risk_class(36), Ok(RiskClass::Medium));
        assert_eq!(risk_class(71), Ok(RiskClass::Extreme));
        assert!(risk_score(0, 1, 1).is_err());
    }

    #[test]
    fn tritest_names_missing_fields() {
        let result = tri_test("deck", "", "closure", "hash");
        assert!(!result.insurable);
        assert_eq!(result.missing, vec!["probabilityBasis"]);
    }
}
