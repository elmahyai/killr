use pyo3::prelude::*;

#[pyfunction]
fn rawmatch(needle: &[u8], haystack: &[u8]) -> Option<usize> {
    if needle.is_empty() || needle.len() > haystack.len() { return None; }
    haystack.windows(needle.len()).position(|w| w == needle).map(|i| i + 1)
}

#[pymodule]
fn mimeparse(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rawmatch, m)?)?;
    Ok(())
}
