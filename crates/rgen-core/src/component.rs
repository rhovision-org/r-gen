use crate::error::RgenError;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ComponentKey {
    Root,
    Clock,
    Verifier,
    Codec,
    AdminGuard,
    Admin,
    Identity,
    CredentialBook,
    Token,
    WorkBook,
    KAssetBook,
    ProvenanceBook,
    RiskBook,
    Payments,
    Oracle,
}

impl ComponentKey {
    pub const ALL: [ComponentKey; 15] = [
        ComponentKey::Root,
        ComponentKey::Clock,
        ComponentKey::Verifier,
        ComponentKey::Codec,
        ComponentKey::AdminGuard,
        ComponentKey::Admin,
        ComponentKey::Identity,
        ComponentKey::CredentialBook,
        ComponentKey::Token,
        ComponentKey::WorkBook,
        ComponentKey::KAssetBook,
        ComponentKey::ProvenanceBook,
        ComponentKey::RiskBook,
        ComponentKey::Payments,
        ComponentKey::Oracle,
    ];

    pub fn key(self) -> &'static str {
        match self {
            ComponentKey::Root => "component:root",
            ComponentKey::Clock => "component:clock",
            ComponentKey::Verifier => "component:verifier",
            ComponentKey::Codec => "component:codec",
            ComponentKey::AdminGuard => "component:admin-guard",
            ComponentKey::Admin => "component:admin",
            ComponentKey::Identity => "component:identity",
            ComponentKey::CredentialBook => "component:credential-book",
            ComponentKey::Token => "component:token",
            ComponentKey::WorkBook => "component:work-book",
            ComponentKey::KAssetBook => "component:kasset-book",
            ComponentKey::ProvenanceBook => "component:provenance-book",
            ComponentKey::RiskBook => "component:risk-book",
            ComponentKey::Payments => "component:payments",
            ComponentKey::Oracle => "component:oracle",
        }
    }

    pub fn parse(key: &str) -> Result<Self, RgenError> {
        Self::ALL
            .into_iter()
            .find(|component| component.key() == key)
            .ok_or(RgenError::UnknownComponent)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip() {
        for component in ComponentKey::ALL {
            assert_eq!(ComponentKey::parse(component.key()), Ok(component));
        }
    }
}
