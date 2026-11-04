//! A small synchronous HTTP reader for the node's public API.
//!
//! This is the `doctor`/CLI read surface. The browser uses [`crate::Client`] instead.

use serde_json::Value;

use crate::error::SdkError;

/// A read-only client for the node's public HTTP API.
pub struct NodeReader {
    node: String,
    http: ureq::Agent,
}

impl NodeReader {
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
            .ok_or_else(|| SdkError::Decode("status has no latestBlockNumber".into()))
    }

    /// Exploratory deploy. The body is a bare JSON string containing the Rholang term.
    pub fn explore(&self, term: &str) -> Result<Value, SdkError> {
        let body = serde_json::to_string(term).map_err(|e| SdkError::Decode(e.to_string()))?;
        let response = self
            .http
            .post(&format!("{}/api/v1/explore-deploy", self.node))
            .set("Content-Type", "application/json")
            .send_string(&body)?;
        Ok(response.into_json()?)
    }

    /// Resolve a component through a GenRoot URI. `GenRoot.resolve` is `(key, ret)`.
    pub fn resolve(&self, root_uri: &str, key: &str) -> Result<Value, SdkError> {
        let term = format!(
            "new reply, rl(`rho:registry:lookup`), ch in {{ \
             rl!(`{root_uri}`, *ch) | \
             for (Root <- ch) {{ \
               Root!(\"resolve\", \"{key}\", *ch) | \
               for (@r <- ch) {{ reply!(r) }} \
             }} }}"
        );
        self.explore(&term)
    }
}

impl From<ureq::Error> for SdkError {
    fn from(error: ureq::Error) -> Self {
        match error {
            ureq::Error::Status(status, response) => {
                let body = response.into_string().unwrap_or_default();
                SdkError::Decode(format!("node returned {status}: {body}"))
            }
            other => SdkError::Decode(format!("transport: {other}")),
        }
    }
}

impl From<std::io::Error> for SdkError {
    fn from(error: std::io::Error) -> Self {
        SdkError::Decode(format!("transport: {error}"))
    }
}
