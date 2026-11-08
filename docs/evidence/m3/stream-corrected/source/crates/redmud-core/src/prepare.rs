//! One-time validation of trusted developer definitions (never record data).
use crate::{Expr, Plan, Step};
use std::collections::HashSet;

pub(crate) const RESERVED: &[&str] = &[
    "invalid_json",
    "invalid_input",
    "numeric_range",
    "missing_field",
    "null_value",
    "invalid_type",
    "numeric_constraint",
    "not_allowed",
    "overflow",
    "callback_error",
    "depth_limit",
];
pub(crate) fn path(path: &str) -> Result<(), &'static str> {
    if path
        .split('.')
        .any(|p| p.is_empty() || p.contains(['[', ']']))
    {
        return Err("Invalid field path");
    }
    Ok(())
}
impl Expr {
    fn prepare_at(&self, depth: usize) -> Result<(), &'static str> {
        if depth > crate::limits::MAX_DEPTH {
            return Err("Execution depth limit exceeded");
        }
        match self {
            Self::Field { path: p } => path(p),
            Self::Sum { path: p, field } => {
                path(p)?;
                path(field)
            }
            Self::Literal { value } => crate::limits::value_depth(value, 1, "", "parse")
                .map_err(|_| "Literal depth limit exceeded"),
            Self::If { condition, yes, no } => {
                condition.prepare_at(depth + 1)?;
                yes.prepare_at(depth + 1)?;
                no.prepare_at(depth + 1)
            }
            Self::Add { left, right }
            | Self::Sub { left, right }
            | Self::Mul { left, right }
            | Self::Gt { left, right }
            | Self::Ge { left, right }
            | Self::Eq { left, right } => {
                left.prepare_at(depth + 1)?;
                right.prepare_at(depth + 1)
            }
        }
    }
}
impl Plan {
    pub fn prepare(&self) -> Result<(), &'static str> {
        self.prepare_at(1)
    }
    fn prepare_at(&self, depth: usize) -> Result<(), &'static str> {
        if depth > crate::limits::MAX_DEPTH {
            return Err("Execution depth limit exceeded");
        }
        let mut rules = HashSet::new();
        for step in &self.steps {
            match step {
                Step::Require { schema } => {
                    for (p, s) in schema {
                        path(p)?;
                        crate::schema::definition_at(s, depth)?;
                    }
                }
                Step::Map { path: p, plan } => {
                    path(p)?;
                    plan.prepare_at(depth + 1)?;
                }
                Step::Derive { name, expr } => {
                    if name.is_empty() || name.contains(['.', '[', ']']) {
                        return Err("Invalid derived name");
                    }
                    expr.prepare_at(depth)?;
                }
                Step::Check { name, expr, .. } => {
                    if name.is_empty()
                        || !name.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'_')
                        || RESERVED.contains(&name.as_str())
                        || !rules.insert(name)
                    {
                        return Err("Invalid or duplicate rule name");
                    }
                    expr.prepare_at(depth)?;
                }
            }
        }
        Ok(())
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    #[test]
    fn definitions_are_validated() {
        for p in ["", "a..b", "a[0]", ".a", "a."] {
            assert!(path(p).is_err());
        }
        assert!(path("orders.total").is_ok());
        let plan: Plan = serde_json::from_value(
            json!({"steps":[{"op":"derive","name":"a.b","expr":{"op":"literal","value":1}}]}),
        )
        .unwrap();
        assert!(plan.prepare().is_err());
        assert!(serde_json::from_value::<Plan>(json!({"steps":[],"typo":1})).is_err());
    }
}
