use crate::models::Credential;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Requirement {
    pub ctype: String,
    pub discipline: String,
    pub jurisdiction: String,
    pub role: String,
    pub min_level: u8,
}

fn scope_ok(value: &str, wanted: &str, wildcards: &[&str]) -> bool {
    value == wanted || wildcards.contains(&value)
}

/// Local mirror of the on-chain scope check. Advisory only: the chain is authoritative.
pub fn matches(credential: &Credential, requirement: &Requirement) -> bool {
    credential.status == "active"
        && scope_ok(&credential.ctype, &requirement.ctype, &["*"])
        && scope_ok(&credential.discipline, &requirement.discipline, &["*"])
        && scope_ok(
            &credential.jurisdiction,
            &requirement.jurisdiction,
            &["global", "*"],
        )
        && scope_ok(&credential.role, &requirement.role, &["*"])
        && credential.level >= requirement.min_level
}

#[cfg(test)]
mod tests {
    use super::*;

    fn credential() -> Credential {
        Credential {
            id: "cr:test".into(),
            subject: "subject".into(),
            issuer: "issuer".into(),
            ctype: "Validator".into(),
            discipline: "structural".into(),
            jurisdiction: "US-TX".into(),
            role: "validator".into(),
            level: 2,
            evidence_hash: String::new(),
            issued_at: 0,
            expires_at: 0,
            status: "active".into(),
        }
    }

    #[test]
    fn exact_scope_matches() {
        let requirement = Requirement {
            ctype: "Validator".into(),
            discipline: "structural".into(),
            jurisdiction: "US-TX".into(),
            role: "validator".into(),
            min_level: 2,
        };
        assert!(matches(&credential(), &requirement));
    }

    #[test]
    fn wrong_discipline_and_level_refuse() {
        let requirement = Requirement {
            ctype: "Validator".into(),
            discipline: "mechanical".into(),
            jurisdiction: "US-TX".into(),
            role: "validator".into(),
            min_level: 2,
        };
        assert!(!matches(&credential(), &requirement));
        let requirement = Requirement {
            ctype: "Validator".into(),
            discipline: "structural".into(),
            jurisdiction: "US-TX".into(),
            role: "validator".into(),
            min_level: 3,
        };
        assert!(!matches(&credential(), &requirement));
    }
}
