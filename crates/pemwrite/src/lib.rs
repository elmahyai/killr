//! PEM writers matching R/openssl `write.c` (`R_pem_write_*`).

use openssl::pkey::{Id, PKey};
use openssl::pkcs7::Pkcs7;
use openssl::symm::Cipher;
use openssl::x509::X509;

fn pem_write_key(der: &[u8], password: Option<&str>) -> Result<Vec<u8>, openssl::error::ErrorStack> {
    let pkey = PKey::private_key_from_der(der)?;
    match password {
        Some(pass) if !pass.is_empty() => {
            pkey.private_key_to_pem_pkcs8_passphrase(Cipher::des_ede3_cbc(), pass.as_bytes())
        }
        _ => pkey.private_key_to_pem_pkcs8(),
    }
}

fn pem_write_pubkey(der: &[u8]) -> Result<Vec<u8>, openssl::error::ErrorStack> {
    let pkey = PKey::public_key_from_der(der)?;
    pkey.public_key_to_pem()
}

fn pem_write_cert(der: &[u8]) -> Result<Vec<u8>, openssl::error::ErrorStack> {
    let cert = X509::from_der(der)?;
    cert.to_pem()
}

fn pem_write_pkcs7(der: &[u8]) -> Result<Vec<u8>, openssl::error::ErrorStack> {
    let p7 = Pkcs7::from_der(der)?;
    p7.to_pem()
}

fn raw_private_to_der(kind: &str, raw: &[u8]) -> Result<Vec<u8>, openssl::error::ErrorStack> {
    let id = match kind {
        "ed25519" => Id::ED25519,
        "x25519" => Id::X25519,
        _ => panic!("unsupported raw private key kind: {kind}"),
    };
    let pkey = PKey::private_key_from_raw_bytes(raw, id)?;
    pkey.private_key_to_der()
}

fn raw_public_to_der(kind: &str, raw: &[u8]) -> Result<Vec<u8>, openssl::error::ErrorStack> {
    let id = match kind {
        "ed25519" => Id::ED25519,
        "x25519" => Id::X25519,
        _ => panic!("unsupported raw public key kind: {kind}"),
    };
    let pkey = PKey::public_key_from_raw_bytes(raw, id)?;
    pkey.public_key_to_der()
}

#[cfg(feature = "python")]
mod python {
    use super::{
        pem_write_cert, pem_write_key, pem_write_pkcs7, pem_write_pubkey, raw_private_to_der,
        raw_public_to_der,
    };
    use pyo3::exceptions::PyRuntimeError;
    use pyo3::prelude::*;

    fn stack_err(err: openssl::error::ErrorStack) -> PyErr {
        PyRuntimeError::new_err(err.to_string())
    }

    #[pyfunction]
    #[pyo3(signature = (der, password=None))]
    fn write_key(der: &[u8], password: Option<&str>) -> PyResult<Vec<u8>> {
        pem_write_key(der, password).map_err(stack_err)
    }

    #[pyfunction]
    fn write_pubkey(der: &[u8]) -> PyResult<Vec<u8>> {
        pem_write_pubkey(der).map_err(stack_err)
    }

    #[pyfunction]
    fn write_cert(der: &[u8]) -> PyResult<Vec<u8>> {
        pem_write_cert(der).map_err(stack_err)
    }

    #[pyfunction]
    fn write_pkcs7(der: &[u8]) -> PyResult<Vec<u8>> {
        pem_write_pkcs7(der).map_err(stack_err)
    }

    #[pyfunction]
    fn private_der_from_raw(kind: &str, raw: &[u8]) -> PyResult<Vec<u8>> {
        raw_private_to_der(kind, raw).map_err(stack_err)
    }

    #[pyfunction]
    fn public_der_from_raw(kind: &str, raw: &[u8]) -> PyResult<Vec<u8>> {
        raw_public_to_der(kind, raw).map_err(stack_err)
    }

    #[pymodule]
    fn pemwrite(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(write_key, m)?)?;
        m.add_function(wrap_pyfunction!(write_pubkey, m)?)?;
        m.add_function(wrap_pyfunction!(write_cert, m)?)?;
        m.add_function(wrap_pyfunction!(write_pkcs7, m)?)?;
        m.add_function(wrap_pyfunction!(private_der_from_raw, m)?)?;
        m.add_function(wrap_pyfunction!(public_der_from_raw, m)?)?;
        Ok(())
    }
}
