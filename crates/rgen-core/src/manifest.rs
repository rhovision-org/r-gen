//! The deployment manifest written by `harness/install.py`.
//!
//! The Root is the authority. The component map is a convenience copy; a client resolves
//! each key through `GenRoot.resolve` and treats a mismatch as a stale manifest.

use std::collections::BTreeMap;

use rcash_core::assets::RegistryUri;
use serde::{Deserialize, Serialize};

use crate::component::ComponentKey;
use crate::error::{Result, RgenError};

/// A deployment manifest: the Root URI plus the installer's component copies.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct Manifest {
    pub root_uri: RegistryUri,
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub components: BTreeMap<String, String>,
}

impl Manifest {
    pub fn from_json(document: &str) -> Result<Self> {
        let value: serde_json::Value = serde_json::from_str(document)
            .map_err(|error| RgenError::Manifest(error.to_string()))?;
        let root = value
            .get("root_uri")
            .and_then(serde_json::Value::as_str)
            .ok_or_else(|| RgenError::Manifest("missing root_uri".into()))?;
        let root_uri = RegistryUri::new(root)?;
        let components = value
            .get("components")
            .cloned()
            .map(serde_json::from_value)
            .transpose()
            .map_err(|error| RgenError::Manifest(format!("components: {error}")))?
            .unwrap_or_default();
        Ok(Self {
            root_uri,
            components,
        })
    }

    pub fn to_json(&self) -> String {
        serde_json::to_string(self).expect("manifest serializes")
    }

    pub fn root_uri(&self) -> &RegistryUri {
        &self.root_uri
    }

    /// The installer's URI for a component, if the manifest carries one.
    pub fn component(&self, key: ComponentKey) -> Result<RegistryUri> {
        let value = self.components.get(key.manifest_name()).ok_or_else(|| {
            RgenError::Manifest(format!("manifest has no {}", key.manifest_name()))
        })?;
        Ok(RegistryUri::new(value)?)
    }

    /// Keys the manifest is missing. An empty list is required for a usable client.
    pub fn missing(&self) -> Vec<ComponentKey> {
        ComponentKey::ALL
            .into_iter()
            .filter(|key| !self.components.contains_key(key.manifest_name()))
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_the_installer_shape() {
        let manifest = Manifest::from_json(
            r#"{"root_uri":"rho:id:abc123","components":{"root":"rho:id:abc123","claim-factory":"rho:id:def456"}}"#,
        )
        .unwrap();
        assert_eq!(manifest.root_uri.as_str(), "rho:id:abc123");
        assert_eq!(
            manifest
                .component(ComponentKey::ClaimFactory)
                .unwrap()
                .as_str(),
            "rho:id:def456"
        );
        assert_eq!(manifest.missing().len(), 7);
    }

    #[test]
    fn components_are_optional() {
        let manifest = Manifest::from_json(r#"{"root_uri":"rho:id:abc123"}"#).unwrap();
        assert!(manifest.components.is_empty());
        assert_eq!(manifest.missing().len(), 9);
    }

    #[test]
    fn refuses_a_non_registry_root() {
        assert!(Manifest::from_json(r#"{"root_uri":"http://example.com"}"#).is_err());
    }
}
