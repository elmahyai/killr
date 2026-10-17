//! Sediment oxygen consumption derivatives from deSolve `src/ex_SCOC.c`.

/// State derivative and two global outputs (Mineralisation, Depo).
#[inline]
pub fn scocder(k: f64, y: f64, depo: f64) -> (f64, f64, f64) {
    let ydot = -k * y + depo;
    let mineralisation = k * y;
    (ydot, mineralisation, depo)
}

#[cfg(feature = "python")]
mod python {
    use super::scocder;
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    #[pyfunction]
    fn scocder_py(k: f64, y: f64, depo: f64) -> PyResult<(f64, f64, f64)> {
        if !k.is_finite() || !y.is_finite() || !depo.is_finite() {
            return Err(PyValueError::new_err("k, y, and depo must be finite"));
        }
        Ok(scocder(k, y, depo))
    }

    #[pymodule]
    fn scoc(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(scocder_py, m)?)?;
        Ok(())
    }
}
