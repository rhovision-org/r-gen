use serde_json::Value;

use crate::error::SdkError;

/// A read-only client for the node's public HTTP API. Writes still go through the
/// `rcash-sdk` deploy path; this type is the `doctor`/read surface.
pub struct Client {
    node: String,
    http: ureq::Agent,
}

impl Client {
    pub fn new(node: impl Into<String>) -> Self {
        Self {
            node: node.into().trim_end_matches('/').to_string(),
            http: ureq::AgentBuilder::new().build(),
        }
    }

    pub fn node(&self) -> &str {
        &self.node
    }

    pub fn status(&self) -> Result<Value, SdkError> {
        let response = self
            .http
            .get(&format!("{}/api/v1/status", self.node))
            .call()?;
        Ok(response.into_json()?)
    }

    pub fn height(&self) -> Result<i64, SdkError> {
        let status = self.status()?;
        status
            .get("latestBlockNumber")
            .and_then(Value::as_i64)
            .ok_or_else(|| SdkError::Manifest("status has no latestBlockNumber".into()))
    }

    /// Exploratory deploy. The body is a bare JSON string containing the Rholang term.
    pub fn explore(&self, term: &str) -> Result<Value, SdkError> {
        let body = serde_json::to_string(term).map_err(|e| SdkError::Json(e.to_string()))?;
        let response = self
            .http
            .post(&format!("{}/api/v1/explore-deploy", self.node))
            .set("Content-Type", "application/json")
            .send_string(&body)?;
        Ok(response.into_json()?)
    }

    /// Resolve a component through a GenRoot URI. The term prints the reply to stdout so the
    /// caller can inspect it in the exploratory result.
    pub fn resolve(&self, root_uri: &str, key: &str) -> Result<Value, SdkError> {
        let term = format!(
            "new rl(`rho:registry:lookup`), ch, out(`rho:io:stdout`) in {{\n\
             \u{20} rl!(`{root_uri}`, *ch) |\n\
             \u{20} for (Root <- ch) {{\n\
             \u{20}   Root!(\"resolve\", \"{key}\", 1, *ch) |\n\
             \u{20}   for (@r <- ch) {{ out!(r) }}\n\
             \u{20} }}\n\
             }}"
        );
        self.explore(&term)
    }
}
