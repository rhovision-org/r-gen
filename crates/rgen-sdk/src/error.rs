use thiserror::Error;

#[derive(Debug, Error)]
pub enum SdkError {
    #[error("transport: {0}")]
    Transport(String),
    #[error("node returned {status}: {body}")]
    Http { status: u16, body: String },
    #[error("json: {0}")]
    Json(String),
    #[error("refused: {0}")]
    Refused(String),
    #[error("manifest: {0}")]
    Manifest(String),
}

impl From<ureq::Error> for SdkError {
    fn from(error: ureq::Error) -> Self {
        match error {
            ureq::Error::Status(status, response) => {
                let body = response.into_string().unwrap_or_default();
                SdkError::Http { status, body }
            }
            other => SdkError::Transport(other.to_string()),
        }
    }
}

impl From<std::io::Error> for SdkError {
    fn from(error: std::io::Error) -> Self {
        SdkError::Transport(error.to_string())
    }
}
