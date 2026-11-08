//! Explicit diagnostic only: no production timers or Python-facing API.
use super::*;
use std::{env, fs, path::PathBuf, time::Instant};

#[test]
#[ignore = "diagnostic: requires REDMUD_BENCH_FIXTURE_DIR and REDMUD_BENCH_OUTPUT"]
fn measure_fixture() {
    let root = PathBuf::from(env::var_os("REDMUD_BENCH_FIXTURE_DIR").expect("fixture directory"));
    let definition = fs::read(root.join("plan.json")).unwrap();
    let plan: Plan = serde_json::from_value(json::parse_plan(&definition).unwrap()).unwrap();
    plan.prepare().unwrap();
    let input = fs::read(root.join("records.jsonl")).unwrap();
    let records: Vec<&[u8]> = input
        .split(|b| *b == b'\n')
        .filter(|r| !r.is_empty())
        .collect();
    assert!(!records.is_empty());
    for raw in records.iter().take(64) {
        std::hint::black_box(plan.run(raw).to_string());
    }
    // Same Rust loop and materialization as NativePlan.run_batch, without FFI.
    let start = Instant::now();
    let production: Vec<String> = records.iter().map(|r| plan.run(r).to_string()).collect();
    let full_ns = start.elapsed().as_nanos();
    let (mut parse_ns, mut evaluate_ns, mut serialize_ns) = (0u128, 0u128, 0u128);
    let mut staged = Vec::with_capacity(records.len());
    for raw in &records {
        let start = Instant::now();
        let parsed = json::parse(raw);
        parse_ns += start.elapsed().as_nanos();
        let start = Instant::now();
        let evaluated = parsed.and_then(|mut value| {
            plan.execute(&mut value, "")?;
            limits::value_depth(&value, 1, "", "transform")?;
            Ok(value)
        });
        evaluate_ns += start.elapsed().as_nanos();
        let start = Instant::now();
        let envelope = match evaluated {
            Ok(value) => json!({"value":value,"errors":[]}),
            Err(error) => json!({"value":null,"errors":[error]}),
        };
        staged.push(envelope.to_string());
        serialize_ns += start.elapsed().as_nanos();
    }
    assert_eq!(
        production, staged,
        "diagnostic scopes must preserve production results"
    );
    // Cross-language parity is checked by the Python driver, outside timing.
    fs::write(
        env::var_os("REDMUD_BENCH_OUTPUT").expect("diagnostic output path"),
        serde_json::to_vec(&production).unwrap(),
    )
    .unwrap();
    println!(
        "REDMUD_COMPONENTS {}",
        json!({"records":records.len(),"full_ns":full_ns,"parse_ns":parse_ns,
               "evaluate_ns":evaluate_ns,"serialize_ns":serialize_ns})
    );
}
