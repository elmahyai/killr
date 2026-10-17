//! R/openssl `R_diffie_hellman` (src/diffie.c): EVP_PKEY_derive on DER keys.

use openssl::derive::Deriver;
use openssl::pkey::PKey;

fn diffie_hellman_der(private_der: &[u8], peer_public_der: &[u8]) -> Result<Vec<u8>, openssl::error::ErrorStack> {
    let pkey = PKey::private_key_from_der(private_der)?;
    let peer = PKey::public_key_from_der(peer_public_der)?;
    let mut deriver = Deriver::new(&pkey)?;
    deriver.set_peer(&peer)?;
    deriver.derive_to_vec()
}

#[cfg(feature = "python")]
mod python {
    use super::diffie_hellman_der;
    use pyo3::prelude::*;
    use pyo3::types::PyBytes;

    #[pyfunction]
    fn derive<'py>(
        py: Python<'py>,
        private_der: &[u8],
        peer_public_der: &[u8],
    ) -> PyResult<Bound<'py, PyBytes>> {
        let out = diffie_hellman_der(private_der, peer_public_der).map_err(|err| {
            pyo3::exceptions::PyRuntimeError::new_err(err.to_string())
        })?;
        Ok(PyBytes::new(py, &out))
    }

    #[pymodule]
    fn ecdhdh(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(derive, m)?)?;
        Ok(())
    }
}
