use crate::error::RgenError;

/// The nine components registered by the current seven-term core.
///
/// `manifest_name` is the key used in `deployments/{devnet,testnet}.json`.
/// `key` is the name registered in the on-chain `GenRoot`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum ComponentKey {
    Root,
    IdentityFactory,
    IdentityDirectory,
    Issuer,
    CredentialFactory,
    OracleFactory,
    ProvenanceFactory,
    ValuePropositionFactory,
    ClaimFactory,
}

impl ComponentKey {
    pub const ALL: [ComponentKey; 9] = [
        ComponentKey::Root,
        ComponentKey::IdentityFactory,
        ComponentKey::IdentityDirectory,
        ComponentKey::Issuer,
        ComponentKey::CredentialFactory,
        ComponentKey::OracleFactory,
        ComponentKey::ProvenanceFactory,
        ComponentKey::ValuePropositionFactory,
        ComponentKey::ClaimFactory,
    ];

    /// The manifest key, e.g. `identity-factory`.
    pub fn manifest_name(self) -> &'static str {
        match self {
            ComponentKey::Root => "root",
            ComponentKey::IdentityFactory => "identity-factory",
            ComponentKey::IdentityDirectory => "identity-directory",
            ComponentKey::Issuer => "issuer",
            ComponentKey::CredentialFactory => "credential-factory",
            ComponentKey::OracleFactory => "oracle-factory",
            ComponentKey::ProvenanceFactory => "provenance-factory",
            ComponentKey::ValuePropositionFactory => "value-proposition-factory",
            ComponentKey::ClaimFactory => "claim-factory",
        }
    }

    /// The on-chain Root key, e.g. `component:identity-factory`.
    pub fn key(self) -> &'static str {
        match self {
            ComponentKey::Root => "component:root",
            ComponentKey::IdentityFactory => "component:identity-factory",
            ComponentKey::IdentityDirectory => "component:identity-directory",
            ComponentKey::Issuer => "component:issuer",
            ComponentKey::CredentialFactory => "component:credential-factory",
            ComponentKey::OracleFactory => "component:oracle-factory",
            ComponentKey::ProvenanceFactory => "component:provenance-factory",
            ComponentKey::ValuePropositionFactory => "component:value-proposition-factory",
            ComponentKey::ClaimFactory => "component:claim-factory",
        }
    }

    pub fn parse(key: &str) -> Result<Self, RgenError> {
        Self::ALL
            .into_iter()
            .find(|component| component.key() == key || component.manifest_name() == key)
            .ok_or_else(|| RgenError::UnknownComponent(key.to_string()))
    }
}

impl std::fmt::Display for ComponentKey {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(self.manifest_name())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip() {
        for component in ComponentKey::ALL {
            assert_eq!(ComponentKey::parse(component.key()), Ok(component));
            assert_eq!(
                ComponentKey::parse(component.manifest_name()),
                Ok(component)
            );
        }
    }

    #[test]
    fn matches_the_installed_catalogue() {
        let keys: Vec<_> = ComponentKey::ALL
            .iter()
            .map(|component| component.key())
            .collect();
        assert_eq!(
            keys,
            vec![
                "component:root",
                "component:identity-factory",
                "component:identity-directory",
                "component:issuer",
                "component:credential-factory",
                "component:oracle-factory",
                "component:provenance-factory",
                "component:value-proposition-factory",
                "component:claim-factory",
            ]
        );
    }
}
