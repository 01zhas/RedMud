//! Parse with serde_json while range-checking integral tokens before conversion.
//! RawValue preserves token text; serde_json owns all JSON syntax validation.
use crate::{err, join, Result};
use serde_json::{value::RawValue, Value};
use std::collections::BTreeMap;

pub fn parse(raw: &[u8]) -> Result<Value> {
    parse_with_limit(raw, crate::limits::MAX_DEPTH)
}
pub fn parse_plan(raw: &[u8]) -> Result<Value> {
    parse_with_limit(raw, crate::limits::CONFIG_DEPTH)
}
fn parse_with_limit(raw: &[u8], max: usize) -> Result<Value> {
    let raw: &RawValue =
        serde_json::from_slice(raw).map_err(|_| err("invalid_json", "", "parse"))?;
    convert(raw, "", 1, max)
}
fn convert(raw: &RawValue, path: &str, depth: usize, max: usize) -> Result<Value> {
    if depth > max {
        return Err(err("depth_limit", path, "parse"));
    }
    let text = raw.get();
    match text.as_bytes()[0] {
        b'{' => {
            let fields: BTreeMap<String, &RawValue> =
                serde_json::from_str(text).map_err(|_| err("invalid_json", path, "parse"))?;
            let mut result = serde_json::Map::new();
            for (k, v) in fields {
                result.insert(k.clone(), convert(v, &join(path, &k), depth + 1, max)?);
            }
            Ok(Value::Object(result))
        }
        b'[' => {
            let items: Vec<&RawValue> =
                serde_json::from_str(text).map_err(|_| err("invalid_json", path, "parse"))?;
            items
                .iter()
                .enumerate()
                .map(|(i, v)| convert(v, &format!("{path}[{i}]"), depth + 1, max))
                .collect::<Result<Vec<_>>>()
                .map(Value::Array)
        }
        b'-' | b'0'..=b'9' if !text.contains(['.', 'e', 'E']) => {
            if let Ok(n) = text.parse::<i64>() {
                Ok(n.into())
            } else if let Ok(n) = text.parse::<u64>() {
                Ok(n.into())
            } else {
                Err(err("numeric_range", path, "parse"))
            }
        }
        _ => serde_json::from_str(text).map_err(|_| err("invalid_json", path, "parse")),
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn integral_tokens_are_never_floats() {
        for text in [
            "-9223372036854775808",
            "9007199254740993",
            "18446744073709551615",
        ] {
            let value = parse(text.as_bytes()).unwrap();
            assert!(!value.is_f64());
            assert_eq!(value.to_string(), text);
        }
        for text in [
            "-9223372036854775809",
            "18446744073709551616",
            "18446744073709551617",
        ] {
            assert_eq!(parse(text.as_bytes()).unwrap_err().code, "numeric_range");
        }
        assert!(parse(br#"{"$serde_json::private::Number":"x"}"#)
            .unwrap()
            .is_object());
        assert_eq!(
            parse(br#"{"x":[18446744073709551617]}"#).unwrap_err().path,
            "x[0]"
        );
        assert!(parse(b"1e999").is_err());
    }
}
