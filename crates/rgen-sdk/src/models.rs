//! Wire-value decoding.
//!
//! The contracts return ordinary Rholang maps and lists. The node drops `Nil` map
//! values, so a missing optional field is absent rather than `null`; the TypeScript views
//! treat them as optional. This module does not re-declare seven Rust view structs — the
//! contract state is the schema, and the UI renders it generically.

use rcash_chain::rho_expr::RhoValue;
use serde_json::{json, Value};

/// Convert a decoded Rholang value to JSON.
pub fn to_json(value: &RhoValue) -> Value {
    match value {
        RhoValue::Par(items)
        | RhoValue::Tuple(items)
        | RhoValue::List(items)
        | RhoValue::Set(items) => Value::Array(items.iter().map(to_json).collect()),
        RhoValue::Map(map) => {
            let mut object = serde_json::Map::with_capacity(map.len());
            for (key, item) in map {
                object.insert(key.clone(), to_json(item));
            }
            Value::Object(object)
        }
        RhoValue::Bool(flag) => Value::Bool(*flag),
        RhoValue::Int(number) => json!(number),
        RhoValue::Str(text) | RhoValue::Uri(text) => Value::String(text.clone()),
        RhoValue::Bytes(hex) => Value::String(hex.clone()),
        RhoValue::Unforg { kind, hex } => json!({"unforgeable": kind, "hex": hex}),
    }
}

/// A single reply payload: one value, a tuple of values, or `null`.
pub fn values_json(values: &[RhoValue]) -> Value {
    match values {
        [] => Value::Null,
        [one] => to_json(one),
        many => Value::Array(many.iter().map(to_json).collect()),
    }
}

/// The `status` field of a state map, if present.
pub fn status(value: &Value) -> Option<&str> {
    value.get("status").and_then(Value::as_str)
}

/// Read a string field.
pub fn text<'a>(value: &'a Value, key: &str) -> Option<&'a str> {
    value.get(key).and_then(Value::as_str)
}

/// Read an integer field.
pub fn integer(value: &Value, key: &str) -> Option<i64> {
    value.get(key).and_then(Value::as_i64)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;

    #[test]
    fn converts_maps_lists_and_uris() {
        let mut map = BTreeMap::new();
        map.insert("uri".to_string(), RhoValue::Uri("rho:id:abc".to_string()));
        map.insert("version".to_string(), RhoValue::Int(1));
        map.insert(
            "writers".to_string(),
            RhoValue::List(vec![RhoValue::Str("alice".into())]),
        );
        let json = to_json(&RhoValue::Map(map));
        assert_eq!(json["uri"], "rho:id:abc");
        assert_eq!(json["version"], 1);
        assert_eq!(json["writers"][0], "alice");
    }

    #[test]
    fn values_json_unwraps_a_single_reply() {
        assert_eq!(values_json(&[]), Value::Null);
        assert_eq!(values_json(&[RhoValue::Int(3)]), json!(3));
        assert_eq!(
            values_json(&[RhoValue::Int(3), RhoValue::Bool(true)]),
            json!([3, true])
        );
    }
}
