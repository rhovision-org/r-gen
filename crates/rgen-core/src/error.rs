use thiserror::Error;

#[derive(Debug, Error, PartialEq, Eq)]
pub enum RgenError {
    #[error("factor out of range: {0}")]
    FactorRange(&'static str),
    #[error("quality dimension out of range")]
    Quality,
    #[error("basis points out of range")]
    Bps,
    #[error("bad identifier: {0}")]
    Id(String),
    #[error("unknown component: {0}")]
    UnknownComponent(String),
    #[error("unsupported action")]
    UnsupportedAction,
    #[error(transparent)]
    Core(#[from] rcash_core::CoreError),
    #[error("manifest: {0}")]
    Manifest(String),
    #[error("json: {0}")]
    Json(String),
    #[error("validation: {0}")]
    Validation(String),
    #[error("term is {actual} bytes; the budget is {limit}")]
    TermTooLarge { actual: usize, limit: usize },
}

/// The pure-layer result type.
pub type Result<T> = std::result::Result<T, RgenError>;
