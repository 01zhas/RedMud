use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use redmud_core::Plan;
#[pyclass]
struct NativePlan {
    plan: Plan,
}
#[pymethods]
impl NativePlan {
    #[new]
    fn new(spec: &str) -> PyResult<Self> {
        let value = redmud_core::json::parse_plan(spec.as_bytes())
            .map_err(|_| PyValueError::new_err("Invalid execution plan"))?;
        let plan: Plan = serde_json::from_value(value)
            .map_err(|_| PyValueError::new_err("Invalid execution plan"))?;
        plan.prepare().map_err(PyValueError::new_err)?;
        Ok(Self { plan })
    }
    fn run_batch(&self, py: Python<'_>, records: Vec<Vec<u8>>) -> Vec<String> {
        py.detach(|| {
            records
                .iter()
                .map(|r| self.plan.run(r).to_string())
                .collect()
        })
    }
}
#[pymodule(gil_used = true)]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<NativePlan>()?;
    Ok(())
}
