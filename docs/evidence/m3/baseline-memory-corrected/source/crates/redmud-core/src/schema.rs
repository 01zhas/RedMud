//! Validate schema definitions once; record validation stays in the executor.
use crate::prepare::path;
use serde_json::Value;
pub(crate) fn kind(spec: &Value) -> &str {
    spec.as_str()
        .or_else(|| spec.get("type").and_then(Value::as_str))
        .unwrap_or(if spec.get("items").is_some() {
            "list"
        } else {
            "object"
        })
}
pub(crate) fn matches(v: &Value, typ: &str) -> bool {
    match typ {
        "int" => v.as_i64().is_some() && !v.is_f64(),
        "float" => v.is_f64(),
        "number" => v.is_number(),
        "str" => v.is_string(),
        "bool" => v.is_boolean(),
        "list" => v.is_array(),
        "object" => v.is_object(),
        _ => false,
    }
}
#[cfg(test)]
pub(crate) fn definition(spec: &Value) -> Result<(), &'static str> {
    definition_at(spec, 1)
}
pub(crate) fn definition_at(spec: &Value, depth: usize) -> Result<(), &'static str> {
    if depth > crate::limits::MAX_DEPTH {
        return Err("Schema depth limit exceeded");
    }
    const BAD: &str = "Invalid schema definition";
    if let Some(obj) = spec.as_object() {
        if obj.keys().any(|k| {
            !matches!(
                k.as_str(),
                "type" | "nullable" | "min" | "max" | "allowed" | "fields" | "items"
            )
        }) {
            return Err(BAD);
        }
        if let Some(t) = obj.get("type") {
            if !t.is_string() {
                return Err(BAD);
            }
        } else if obj.contains_key("fields") == obj.contains_key("items") {
            return Err(BAD);
        }
        if obj.get("nullable").is_some_and(|v| !v.is_boolean()) {
            return Err(BAD);
        }
    } else if !spec.is_string() {
        return Err(BAD);
    }
    let typ = kind(spec);
    if !matches!(
        typ,
        "int" | "float" | "number" | "str" | "bool" | "list" | "object"
    ) {
        return Err(BAD);
    }
    for bound in ["min", "max"] {
        if let Some(b) = spec.get(bound) {
            if !matches!(typ, "int" | "float") || !matches(b, typ) {
                return Err(BAD);
            }
        }
    }
    if let (Some(a), Some(b)) = (spec.get("min"), spec.get("max")) {
        let ordered = if typ == "int" {
            a.as_i64() <= b.as_i64()
        } else {
            a.as_f64() <= b.as_f64()
        };
        if !ordered {
            return Err(BAD);
        }
    }
    if let Some(values) = spec.get("allowed") {
        let values = values.as_array().ok_or(BAD)?;
        if values.is_empty()
            || values.iter().any(|v| {
                !(matches(v, typ)
                    || (v.is_null() && spec.get("nullable") == Some(&Value::Bool(true))))
            })
        {
            return Err(BAD);
        }
    }
    if let Some(values) = spec.get("allowed").and_then(Value::as_array) {
        for value in values {
            crate::limits::value_depth(value, 1, "", "parse")
                .map_err(|_| "Allowed value depth limit exceeded")?;
        }
    }
    if let Some(fields) = spec.get("fields") {
        if typ != "object" {
            return Err(BAD);
        }
        for (p, s) in fields.as_object().ok_or(BAD)? {
            path(p)?;
            definition_at(s, depth + 1)?;
        }
    }
    if let Some(items) = spec.get("items") {
        if typ != "list" {
            return Err(BAD);
        }
        definition_at(items, depth + 1)?;
    }
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    #[test]
    fn schemas_are_checked_once() {
        for spec in [
            json!({}),
            json!("bad"),
            json!({"type":"int","min":1.0}),
            json!({"items":"bad"}),
            json!({"type":"bool","allowed":[1]}),
        ] {
            assert!(definition(&spec).is_err());
        }
        assert!(definition(&json!({"items":{"fields":{"x":"int"}}})).is_ok());
    }
}
