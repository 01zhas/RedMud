pub mod json;
pub mod limits;
mod prepare;
mod schema;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

#[derive(Clone, Debug, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case", deny_unknown_fields)]
pub enum Expr {
    Field {
        path: String,
    },
    Literal {
        value: Value,
    },
    Add {
        left: Box<Expr>,
        right: Box<Expr>,
    },
    Sub {
        left: Box<Expr>,
        right: Box<Expr>,
    },
    Mul {
        left: Box<Expr>,
        right: Box<Expr>,
    },
    Gt {
        left: Box<Expr>,
        right: Box<Expr>,
    },
    Ge {
        left: Box<Expr>,
        right: Box<Expr>,
    },
    Eq {
        left: Box<Expr>,
        right: Box<Expr>,
    },
    If {
        condition: Box<Expr>,
        yes: Box<Expr>,
        no: Box<Expr>,
    },
    Sum {
        path: String,
        field: String,
    },
}
#[derive(Clone, Debug, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case", deny_unknown_fields)]
pub enum Step {
    Require {
        schema: std::collections::BTreeMap<String, Value>,
    },
    Check {
        name: String,
        expr: Expr,
        message: String,
    },
    Derive {
        name: String,
        expr: Expr,
    },
    Map {
        path: String,
        plan: Plan,
    },
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Plan {
    pub steps: Vec<Step>,
}
#[derive(Debug, Serialize)]
pub struct Error {
    pub code: String,
    pub path: String,
    pub stage: String,
    pub message: String,
}
type Result<T> = std::result::Result<T, Error>;
fn err(code: &str, path: &str, stage: &str) -> Error {
    Error {
        code: code.into(),
        path: path.into(),
        stage: stage.into(),
        message: code.replace('_', " "),
    }
}
fn join(base: &str, path: &str) -> String {
    if base.is_empty() {
        path.into()
    } else {
        format!("{base}.{path}")
    }
}
fn get<'a>(v: &'a Value, path: &str, base: &str) -> Result<&'a Value> {
    get_at(v, path, base, "validation")
}
fn get_at<'a>(v: &'a Value, path: &str, base: &str, stage: &str) -> Result<&'a Value> {
    let mut current = v;
    let mut prefix = base.to_owned();
    for key in path.split('.') {
        if !current.is_object() {
            return Err(err(
                if current.is_null() {
                    "null_value"
                } else {
                    "invalid_type"
                },
                &prefix,
                stage,
            ));
        }
        prefix = join(&prefix, key);
        current = current
            .get(key)
            .ok_or_else(|| err("missing_field", &prefix, stage))?;
    }
    Ok(current)
}

fn integer(v: &Value, path: &str) -> Result<i64> {
    v.as_i64().ok_or_else(|| {
        err(
            if v.is_null() {
                "null_value"
            } else {
                "invalid_type"
            },
            path,
            "transform",
        )
    })
}
impl Expr {
    fn location(&self, base: &str, target: &str) -> String {
        match self {
            Self::Field { path } | Self::Sum { path, .. } => join(base, path),
            _ => target.into(),
        }
    }
    pub fn eval(&self, v: &Value, base: &str) -> Result<Value> {
        self.eval_at(v, base, base)
    }
    fn eval_at(&self, v: &Value, base: &str, target: &str) -> Result<Value> {
        match self {
            Self::Field { path } => Ok(get_at(v, path, base, "transform")?.clone()),
            Self::Literal { value } => Ok(value.clone()),
            Self::If { condition, yes, no } => {
                let cond = condition.eval_at(v, base, target)?;
                match cond.as_bool() {
                    Some(true) => yes.eval_at(v, base, target),
                    Some(false) => no.eval_at(v, base, target),
                    None => Err(err(
                        "invalid_type",
                        &condition.location(base, target),
                        "transform",
                    )),
                }
            }
            Self::Sum { path, field } => {
                let p = join(base, path);
                let value = get_at(v, path, base, "transform")?;
                let list = value.as_array().ok_or_else(|| {
                    err(
                        if value.is_null() {
                            "null_value"
                        } else {
                            "invalid_type"
                        },
                        &p,
                        "transform",
                    )
                })?;
                let mut total = 0i64;
                for (i, item) in list.iter().enumerate() {
                    let b = format!("{p}[{i}]");
                    total = total
                        .checked_add(integer(
                            get_at(item, field, &b, "transform")?,
                            &join(&b, field),
                        )?)
                        .ok_or_else(|| err("overflow", &p, "transform"))?;
                }
                Ok(json!(total))
            }
            _ => {
                let (left, right) = match self {
                    Self::Add { left, right }
                    | Self::Sub { left, right }
                    | Self::Mul { left, right }
                    | Self::Gt { left, right }
                    | Self::Ge { left, right }
                    | Self::Eq { left, right } => (left, right),
                    _ => unreachable!(),
                };
                let a = left.eval_at(v, base, target)?;
                if matches!(self, Self::Eq { .. }) {
                    return Ok(json!(a == right.eval_at(v, base, target)?));
                }
                let x = integer(&a, &left.location(base, target))?;
                let b = right.eval_at(v, base, target)?;
                let y = integer(&b, &right.location(base, target))?;
                match self {
                    Self::Gt { .. } => Ok(json!(x > y)),
                    Self::Ge { .. } => Ok(json!(x >= y)),
                    _ => {
                        let n = match self {
                            Self::Add { .. } => x.checked_add(y),
                            Self::Sub { .. } => x.checked_sub(y),
                            _ => x.checked_mul(y),
                        };
                        n.map(|n| json!(n))
                            .ok_or_else(|| err("overflow", target, "transform"))
                    }
                }
            }
        }
    }
}
fn validate(v: &Value, spec: &Value, path: &str) -> Result<()> {
    let typ = schema::kind(spec);
    if v.is_null() {
        return if spec.get("nullable") == Some(&Value::Bool(true)) {
            Ok(())
        } else {
            Err(err("null_value", path, "validation"))
        };
    }
    let valid = schema::matches(v, typ);
    if !valid {
        return Err(err("invalid_type", path, "validation"));
    }
    for (key, lower) in [("min", true), ("max", false)] {
        if let Some(bound) = spec.get(key) {
            // Integral comparisons retain exactness beyond 2^53.
            let pass = if let (Some(a), Some(b)) = (v.as_i64(), bound.as_i64()) {
                if lower {
                    a >= b
                } else {
                    a <= b
                }
            } else if typ == "float" {
                let (a, b) = (v.as_f64().unwrap(), bound.as_f64().unwrap());
                if lower {
                    a >= b
                } else {
                    a <= b
                }
            } else {
                false
            };
            if !pass {
                return Err(err("numeric_constraint", path, "validation"));
            }
        }
    }
    if let Some(allowed) = spec.get("allowed").and_then(Value::as_array) {
        if !allowed.contains(v) {
            return Err(err("not_allowed", path, "validation"));
        }
    }
    if let Some(fields) = spec.get("fields").and_then(Value::as_object) {
        for (k, s) in fields {
            let p = join(path, k);
            validate(get(v, k, path)?, s, &p)?;
        }
    }
    if let Some(s) = spec.get("items") {
        if let Some(items) = v.as_array() {
            for (i, item) in items.iter().enumerate() {
                validate(item, s, &format!("{path}[{i}]"))?;
            }
        }
    }
    Ok(())
}
impl Plan {
    pub fn execute(&self, v: &mut Value, base: &str) -> Result<()> {
        if !v.is_object() {
            return Err(err("invalid_type", base, "validation"));
        }
        for step in &self.steps {
            match step {
                Step::Require { schema } => {
                    for (path, spec) in schema {
                        validate(get(v, path, base)?, spec, &join(base, path))?;
                    }
                }
                Step::Check {
                    name,
                    expr,
                    message,
                } => {
                    let result = expr.eval(v, base)?;
                    let pass = result.as_bool().ok_or_else(|| {
                        err("invalid_type", &expr.location(base, base), "transform")
                    })?;
                    if !pass {
                        let mut e = err(name, base, "validation");
                        e.message = message.clone();
                        return Err(e);
                    }
                }
                Step::Derive { name, expr } => {
                    let value = expr.eval_at(v, base, &join(base, name))?;
                    v.as_object_mut().unwrap().insert(name.clone(), value);
                }
                Step::Map { path, plan } => {
                    let p = join(base, path);
                    let mut target = &mut *v;
                    let mut prefix = base.to_owned();
                    for key in path.split('.') {
                        if !target.is_object() {
                            return Err(err(
                                if target.is_null() {
                                    "null_value"
                                } else {
                                    "invalid_type"
                                },
                                &prefix,
                                "validation",
                            ));
                        }
                        prefix = join(&prefix, key);
                        target = target
                            .get_mut(key)
                            .ok_or_else(|| err("missing_field", &prefix, "validation"))?;
                    }
                    let code = if target.is_null() {
                        "null_value"
                    } else {
                        "invalid_type"
                    };
                    let items = target
                        .as_array_mut()
                        .ok_or_else(|| err(code, &p, "validation"))?;
                    for (i, item) in items.iter_mut().enumerate() {
                        plan.execute(item, &format!("{p}[{i}]"))?;
                    }
                }
            }
        }
        Ok(())
    }
    pub fn run(&self, raw: &[u8]) -> Value {
        let parsed = json::parse(raw);
        match parsed {
            Err(e) => json!({"value":null,"errors":[e]}),
            Ok(mut v) => match self.execute(&mut v, "") {
                Ok(()) => match limits::value_depth(&v, 1, "", "transform") {
                    Ok(()) => json!({"value":v,"errors":[]}),
                    Err(e) => json!({"value":null,"errors":[e]}),
                },
                Err(e) => json!({"value":null,"errors":[e]}),
            },
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn overflow_and_isolation() {
        let p:Plan=serde_json::from_value(json!({"steps":[{"op":"derive","name":"v","expr":{"op":"mul","left":{"op":"field","path":"x"},"right":{"op":"literal","value":2}}}]})).unwrap();
        assert_eq!(
            p.run(br#"{"x":9223372036854775807}"#)["errors"][0]["code"],
            "overflow"
        );
        assert_eq!(p.run(br#"{"x":2}"#)["value"]["v"], 4);
        assert_eq!(p.run(b"{")["errors"][0]["code"], "invalid_json");
    }
}

#[cfg(test)]
mod validation_tests {
    use super::*;
    #[test]
    fn schema_edges() {
        let spec = json!({"type":"object","fields":{"items":{"type":"list","items":{"type":"int","min":1,"allowed":[1,2]}}}});
        assert!(validate(&json!({"items":[1,2]}), &spec, "").is_ok());
        assert_eq!(
            validate(&json!({"items":[0]}), &spec, "").unwrap_err().path,
            "items[0]"
        );
        assert_eq!(
            validate(&json!({}), &spec, "").unwrap_err().code,
            "missing_field"
        );
        assert!(validate(&Value::Null, &json!({"type":"int","nullable":true}), "x").is_ok());
        assert!(validate(&json!(true), &json!("int"), "x").is_err());
        assert!(validate(
            &json!(9007199254740992i64),
            &json!({"type":"int","min":9007199254740993i64}),
            "x"
        )
        .is_err());
    }
    #[test]
    fn nested_and_empty_sum() {
        let plan:Plan=serde_json::from_value(json!({"steps":[{"op":"map","path":"items","plan":{"steps":[{"op":"require","schema":{"x":"int"}}]}},{"op":"derive","name":"sum","expr":{"op":"sum","path":"items","field":"x"}}]})).unwrap();
        assert_eq!(plan.run(br#"{"items":[]}"#)["value"]["sum"], 0);
        assert_eq!(
            plan.run(br#"{"items":[{"x":1},{"x":2}]}"#)["value"]["sum"],
            3
        );
        assert_eq!(
            plan.run(br#"{"items":[{"x":null}]}"#)["errors"][0]["path"],
            "items[0].x"
        );
    }
}

#[cfg(test)]
mod expression_contract_tests {
    use super::*;
    #[test]
    fn failure_order_paths_and_lazy_branches() {
        let expr:Expr=serde_json::from_value(json!({"op":"add","left":{"op":"field","path":"x"},"right":{"op":"field","path":"absent"}})).unwrap();
        let e = expr.eval(&json!({"x":null}), "row[0]").unwrap_err();
        assert_eq!(
            (e.code.as_str(), e.path.as_str(), e.stage.as_str()),
            ("null_value", "row[0].x", "transform")
        );
        let expr:Expr=serde_json::from_value(json!({"op":"if","condition":{"op":"literal","value":true},"yes":{"op":"literal","value":1},"no":{"op":"field","path":"absent"}})).unwrap();
        assert_eq!(expr.eval(&json!({}), "").unwrap(), json!(1));
    }
}

#[cfg(test)]
mod invariant_tests {
    use super::*;
    #[test]
    fn deterministic_checked_arithmetic_matches_wide_integer_oracle() {
        let edges = [
            i64::MIN,
            i64::MIN + 1,
            -9007199254740993,
            -1,
            0,
            1,
            9007199254740993,
            i64::MAX,
        ];
        for op in ["add", "sub", "mul"] {
            let expr: Expr = serde_json::from_value(
                json!({"op":op,"left":{"op":"field","path":"x"},"right":{"op":"field","path":"y"}}),
            )
            .unwrap();
            for x in edges {
                for y in edges {
                    let wide = match op {
                        "add" => i128::from(x) + i128::from(y),
                        "sub" => i128::from(x) - i128::from(y),
                        _ => i128::from(x) * i128::from(y),
                    };
                    let first = expr.eval(&json!({"x":x,"y":y}), "");
                    match i64::try_from(wide) {
                        Ok(expected) => assert_eq!(first.unwrap(), json!(expected)),
                        Err(_) => assert_eq!(first.unwrap_err().code, "overflow"),
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod depth_contract_tests {
    use super::*;
    #[test]
    fn parser_boundaries_and_adversarial_depth() {
        for depth in [63usize, 64, 65, 1000, 20000] {
            let raw = format!("{}0{}", "[".repeat(depth - 1), "]".repeat(depth - 1));
            let result = json::parse(raw.as_bytes());
            if depth <= 64 {
                assert!(result.is_ok());
            } else {
                assert_eq!(result.unwrap_err().code, "depth_limit");
            }
        }
    }
    #[test]
    fn expression_and_plan_budgets_are_combined() {
        let mut expr = Expr::Field { path: "x".into() };
        for _ in 1..64 {
            expr = Expr::Add {
                left: Box::new(expr),
                right: Box::new(Expr::Literal { value: json!(0) }),
            };
        }
        let plan = Plan {
            steps: vec![Step::Derive {
                name: "v".into(),
                expr,
            }],
        };
        assert!(plan.prepare().is_ok());
        let nested = Plan {
            steps: vec![Step::Map {
                path: "items".into(),
                plan,
            }],
        };
        assert!(nested.prepare().is_err());
    }
}

#[cfg(test)]
mod benchmark_probe;
