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
    #[error("unknown component")]
    UnknownComponent,
    #[error("unsupported action")]
    UnsupportedAction,
}
