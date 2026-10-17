//! xls workbook reader. The readxl-xls agent replaces the bodies.

pub fn sheets(_path: &str) -> Result<Vec<String>, String> {
    Err("xls sheets are not ported".to_string())
}

#[cfg(feature = "python")]
mod python {
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    #[pyfunction]
    #[pyo3(name = "sheets")]
    fn sheets_py(path: String) -> PyResult<Vec<String>> {
        super::sheets(&path).map_err(PyValueError::new_err)
    }

    #[pyfunction]
    #[pyo3(name = "read")]
    fn read_py(
        path: String,
        sheet_i: i32,
        limits: Vec<i32>,
        shim: bool,
        col_names: Bound<'_, PyAny>,
        col_types: Vec<String>,
        na: Vec<String>,
        trim_ws: bool,
        guess_max: i32,
    ) -> PyResult<Py<PyAny>> {
        let _ = (
            path, sheet_i, limits, shim, col_names, col_types, na, trim_ws, guess_max,
        );
        Err(PyValueError::new_err("xls reading is not ported"))
    }

    #[pymodule]
    fn readxls(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(sheets_py, m)?)?;
        m.add_function(wrap_pyfunction!(read_py, m)?)?;
        Ok(())
    }
}
