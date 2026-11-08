//! Finite recursion budgets; JSON syntax remains serde_json's responsibility.
use crate::{err, join, Result};
use serde_json::Value;
pub const MAX_DEPTH: usize = 64;
// Transport wrappers (steps arrays/step objects) are not semantic plan nodes.
pub(crate) const CONFIG_DEPTH: usize = MAX_DEPTH * 4 + 8;
pub(crate) fn value_depth(value: &Value, depth: usize, path: &str, stage: &str) -> Result<()> {
    if depth > MAX_DEPTH {
        return Err(err("depth_limit", path, stage));
    }
    match value {
        Value::Array(items) => {
            for (i, v) in items.iter().enumerate() {
                value_depth(v, depth + 1, &format!("{path}[{i}]"), stage)?;
            }
        }
        Value::Object(fields) => {
            for (k, v) in fields {
                value_depth(v, depth + 1, &join(path, k), stage)?;
            }
        }
        _ => {}
    }
    Ok(())
}
