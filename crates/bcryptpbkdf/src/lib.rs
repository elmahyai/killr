//! OpenBSD bcrypt_pbkdf from the R package openssl `src/bcrypt`.

use std::os::raw::{c_char, c_int, c_uint};

extern "C" {
    fn bcrypt_pbkdf(
        pass: *const c_char,
        passlen: usize,
        salt: *const u8,
        saltlen: usize,
        key: *mut u8,
        keylen: usize,
        rounds: c_uint,
    ) -> c_int;
}

/// Derive `keylen` bytes with the same bcrypt-PBKDF as R `bcrypt_pbkdf`.
pub fn derive_key(pass: &[u8], salt: &[u8], rounds: u32, keylen: usize) -> Result<Vec<u8>, &'static str> {
    if rounds < 1 {
        return Err("rounds must be at least 1");
    }
    if pass.is_empty() || salt.is_empty() || keylen == 0 {
        return Err("password, salt, and size must be non-empty");
    }
    if keylen > 32 * 32 || salt.len() > 1 << 20 {
        return Err("salt or key length out of range");
    }
    let mut key = vec![0u8; keylen];
    let rc = unsafe {
        bcrypt_pbkdf(
            pass.as_ptr() as *const c_char,
            pass.len(),
            salt.as_ptr(),
            salt.len(),
            key.as_mut_ptr(),
            key.len(),
            rounds,
        )
    };
    if rc != 0 {
        return Err("bcrypt key derivation failed");
    }
    Ok(key)
}

#[cfg(feature = "python")]
mod python {
    use super::derive_key;
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;

    #[pyfunction]
    #[pyo3(signature = (password, salt, rounds=16, size=32))]
    fn inner(password: &[u8], salt: &[u8], rounds: u32, size: usize) -> PyResult<Vec<u8>> {
        derive_key(password, salt, rounds, size).map_err(|message| PyValueError::new_err(message))
    }

    #[pymodule]
    fn bcryptpbkdf(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(inner, m)?)?;
        Ok(())
    }
}
