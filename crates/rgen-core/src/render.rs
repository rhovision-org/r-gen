//! Safe JSON-to-Rholang rendering.
//!
//! Rholang strings have no escape processing: a string token runs from one `"` to the
//! next. `rcash_core::rho::quote_str` refuses unrepresentable input, and this module
//! refuses floats rather than emitting a value the node cannot represent.

use serde_json::Value;

use crate::error::{Result, RgenError};

/// The project's per-term budget. The node accepts 64 KiB inclusive; r-gen keeps an
/// 8 KiB margin for templates and quoting growth.
pub const PROJECT_TERM_BUDGET: usize = 56 * 1024;

/// Quote a string for a Rholang term.
pub fn quote_string(value: &str) -> Result<String> {
    Ok(rcash_core::rho::quote_str(value)?)
}

pub fn render_i64(value: i64) -> String {
    value.to_string()
}

pub fn render_bool(value: bool) -> String {
    if value {
        "true".to_string()
    } else {
        "false".to_string()
    }
}

/// Render one JSON value as a Rholang data expression.
///
/// Objects become map literals, arrays become list literals, `null` becomes `Nil`.
/// Floats and integers wider than `i64` are refused.
pub fn render_json(value: &Value) -> Result<String> {
    match value {
        Value::Null => Ok("Nil".to_string()),
        Value::Bool(flag) => Ok(render_bool(*flag)),
        Value::Number(number) => {
            if let Some(value) = number.as_i64() {
                Ok(render_i64(value))
            } else if let Some(value) = number.as_u64() {
                i64::try_from(value)
                    .map(render_i64)
                    .map_err(|_| RgenError::Json(format!("integer is wider than i64: {value}")))
            } else {
                Err(RgenError::Json(format!(
                    "floating-point values are not representable: {number}"
                )))
            }
        }
        Value::String(text) => quote_string(text),
        Value::Array(items) => {
            let rendered = items.iter().map(render_json).collect::<Result<Vec<_>>>()?;
            Ok(format!("[{}]", rendered.join(", ")))
        }
        Value::Object(map) => {
            let mut entries = Vec::with_capacity(map.len());
            for (key, item) in map {
                entries.push(format!("{}: {}", quote_string(key)?, render_json(item)?));
            }
            Ok(format!("{{{}}}", entries.join(", ")))
        }
    }
}

/// Refuse a term over the project budget before it is signed.
pub fn check_project_size(term: &str) -> Result<()> {
    let actual = term.len();
    if actual > PROJECT_TERM_BUDGET {
        return Err(RgenError::TermTooLarge {
            actual,
            limit: PROJECT_TERM_BUDGET,
        });
    }
    rcash_core::rho::check_term_size(term)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn renders_data_deterministically() {
        assert_eq!(render_json(&json!(null)).unwrap(), "Nil");
        assert_eq!(render_json(&json!(true)).unwrap(), "true");
        assert_eq!(render_json(&json!(-3)).unwrap(), "-3");
        assert_eq!(render_json(&json!("a b")).unwrap(), "\"a b\"");
        assert_eq!(
            render_json(&json!({"z": [1, "x"], "a": false})).unwrap(),
            "{\"a\": false, \"z\": [1, \"x\"]}"
        );
    }

    #[test]
    fn refuses_floats_and_injection() {
        assert!(render_json(&json!(1.5)).is_err());
        assert!(render_json(&json!({"k": "a\"b"})).is_err());
        assert!(render_json(&json!({"k": "a\nb"})).is_err());
    }

    #[test]
    fn refuses_oversized_terms() {
        let term = "a".repeat(PROJECT_TERM_BUDGET + 1);
        assert!(matches!(
            check_project_size(&term),
            Err(RgenError::TermTooLarge { .. })
        ));
    }
}
