use openssl::derive::Deriver;
use openssl::pkey::{Id, PKey};
use openssl::sign::{Signer, Verifier};
use openssl::symm::{Cipher, Crypter, Mode};
use std::ffi::CString;
use std::sync::Once;

fn ed25519_from_seed(seed: &[u8]) -> PKey<openssl::pkey::Private> {
    PKey::private_key_from_raw_bytes(seed, Id::ED25519).expect("ed25519 key")
}

fn ed25519_sign_raw(seed: &[u8], data: &[u8]) -> Vec<u8> {
    let key = ed25519_from_seed(seed);
    let mut signer = Signer::new_without_digest(&key).expect("ed25519 signer");
    signer.sign_oneshot_to_vec(data).expect("ed25519 sign")
}

fn ed25519_public_raw(seed: &[u8]) -> Vec<u8> {
    ed25519_from_seed(seed).raw_public_key().expect("ed25519 public")
}

fn ed25519_verify_raw(public: &[u8], data: &[u8], sig: &[u8]) -> bool {
    let key = PKey::public_key_from_raw_bytes(public, Id::ED25519).expect("ed25519 pubkey");
    let mut verifier = Verifier::new_without_digest(&key).expect("ed25519 verifier");
    verifier.verify_oneshot(sig, data).unwrap_or(false)
}

fn x25519_public_raw(seed: &[u8]) -> Vec<u8> {
    PKey::private_key_from_raw_bytes(seed, Id::X25519)
        .expect("x25519 key")
        .raw_public_key()
        .expect("x25519 public")
}

fn x25519_shared(seed: &[u8], peer_public: &[u8]) -> Vec<u8> {
    let key = PKey::private_key_from_raw_bytes(seed, Id::X25519).expect("x25519 key");
    let peer = PKey::public_key_from_raw_bytes(peer_public, Id::X25519).expect("x25519 peer");
    let mut deriver = Deriver::new(&key).expect("x25519 derive");
    deriver.set_peer(&peer).expect("x25519 peer set");
    deriver.derive_to_vec().expect("x25519 secret")
}

fn ensure_legacy() {
    static ONCE: Once = Once::new();
    ONCE.call_once(|| {
        if let Ok(provider) = openssl::provider::Provider::try_load(None, "legacy", true) {
            std::mem::forget(provider);
        }
    });
}

fn digest_hex(algo: &str, data: &[u8]) -> String {
    if algo == "md4" {
        ensure_legacy();
    }
    let name = CString::new(algo).expect("algo name");
    let mut out = vec![0u8; 64];
    let mut length = 0usize;
    let rc = unsafe {
        openssl_sys::EVP_Q_digest(
            std::ptr::null_mut(),
            name.as_ptr(),
            std::ptr::null(),
            data.as_ptr() as *const _,
            data.len(),
            out.as_mut_ptr(),
            &mut length,
        )
    };
    if rc != 1 {
        panic!("unknown digest {algo}");
    }
    out.truncate(length);
    out.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn cipher_for(key: &[u8], mode: &str) -> Cipher {
    match (key.len(), mode) {
        (16, "ctr") => Cipher::aes_128_ctr(),
        (24, "ctr") => Cipher::aes_192_ctr(),
        (32, "ctr") => Cipher::aes_256_ctr(),
        (16, "cbc") => Cipher::aes_128_cbc(),
        (24, "cbc") => Cipher::aes_192_cbc(),
        (32, "cbc") => Cipher::aes_256_cbc(),
        (16, "gcm") => Cipher::aes_128_gcm(),
        (24, "gcm") => Cipher::aes_192_gcm(),
        (32, "gcm") => Cipher::aes_256_gcm(),
        _ => panic!("key must be of length 16, 24, or 32"),
    }
}

fn aes_crypt(data: &[u8], key: &[u8], iv: &[u8], encrypt: bool, kind: &str) -> Vec<u8> {
    if kind == "gcm" {
        if iv.len() != 12 {
            panic!("aes-gcm requires an iv of length 12");
        }
    } else if iv.len() != 16 {
        panic!("aes requires an iv of length 16");
    }
    let cipher = cipher_for(key, kind);
    let mode = if encrypt { Mode::Encrypt } else { Mode::Decrypt };
    let mut crypter = Crypter::new(cipher, mode, key, Some(iv)).expect("aes init");
    if kind == "ctr" || kind == "gcm" {
        crypter.pad(false);
    }
    let mut out = vec![0u8; data.len() + cipher.block_size()];
    let mut count = crypter.update(data, &mut out).expect("aes update");
    match crypter.finalize(&mut out[count..]) {
        Ok(extra) => count += extra,
        Err(_) if kind == "gcm" && !encrypt => {}
        Err(err) => panic!("aes final: {err}"),
    }
    out.truncate(count);
    out
}

#[cfg(feature = "python")]
mod python {
    use super::{
        aes_crypt, digest_hex, ed25519_public_raw, ed25519_sign_raw, ed25519_verify_raw,
        x25519_public_raw, x25519_shared,
    };
    use openssl::pkey::PKey;
    use openssl::rand::rand_bytes;
    use openssl::rsa::Rsa;
    use pyo3::prelude::*;
    use pyo3::types::PyBytes;

    #[pyfunction]
    fn aes_ctr_crypt<'py>(
        py: Python<'py>,
        data: &[u8],
        key: &[u8],
        iv: &[u8],
        encrypt: bool,
    ) -> PyResult<Bound<'py, PyBytes>> {
        let out = aes_crypt(data, key, iv, encrypt, "ctr");
        Ok(PyBytes::new(py, &out))
    }

    #[pyfunction]
    fn aes_gcm_crypt<'py>(
        py: Python<'py>,
        data: &[u8],
        key: &[u8],
        iv: &[u8],
        encrypt: bool,
    ) -> PyResult<Bound<'py, PyBytes>> {
        let out = aes_crypt(data, key, iv, encrypt, "gcm");
        Ok(PyBytes::new(py, &out))
    }

    #[pyfunction]
    fn aes_cbc_crypt<'py>(
        py: Python<'py>,
        data: &[u8],
        key: &[u8],
        iv: &[u8],
        encrypt: bool,
    ) -> PyResult<Bound<'py, PyBytes>> {
        let out = aes_crypt(data, key, iv, encrypt, "cbc");
        Ok(PyBytes::new(py, &out))
    }

    #[pyfunction]
    fn digest_hex_ssl(algo: &str, data: &[u8]) -> PyResult<String> {
        Ok(digest_hex(algo, data))
    }

    #[pyfunction]
    fn rsa_keygen_der<'py>(py: Python<'py>, bits: i32) -> PyResult<Bound<'py, PyBytes>> {
        let rsa = Rsa::generate(bits as u32).map_err(|err| {
            pyo3::exceptions::PyRuntimeError::new_err(err.to_string())
        })?;
        let pkey = PKey::from_rsa(rsa).map_err(|err| {
            pyo3::exceptions::PyRuntimeError::new_err(err.to_string())
        })?;
        let der = pkey.private_key_to_der().map_err(|err| {
            pyo3::exceptions::PyRuntimeError::new_err(err.to_string())
        })?;
        Ok(PyBytes::new(py, &der))
    }

    #[pyfunction]
    fn rand_bytes_ssl<'py>(py: Python<'py>, n: i32) -> PyResult<Bound<'py, PyBytes>> {
        if n < 0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Please provide a numeric value for n",
            ));
        }
        let mut buf = vec![0u8; n as usize];
        rand_bytes(&mut buf).map_err(|err| {
            pyo3::exceptions::PyRuntimeError::new_err(err.to_string())
        })?;
        Ok(PyBytes::new(py, &buf))
    }

    #[pyfunction]
    fn ed25519_sign_ssl<'py>(
        py: Python<'py>,
        seed: &[u8],
        data: &[u8],
    ) -> PyResult<Bound<'py, PyBytes>> {
        Ok(PyBytes::new(py, &ed25519_sign_raw(seed, data)))
    }

    #[pyfunction]
    fn ed25519_public_ssl<'py>(py: Python<'py>, seed: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
        Ok(PyBytes::new(py, &ed25519_public_raw(seed)))
    }

    #[pyfunction]
    fn ed25519_verify_ssl(public: &[u8], data: &[u8], sig: &[u8]) -> PyResult<bool> {
        Ok(ed25519_verify_raw(public, data, sig))
    }

    #[pyfunction]
    fn x25519_public_ssl<'py>(py: Python<'py>, seed: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
        Ok(PyBytes::new(py, &x25519_public_raw(seed)))
    }

    #[pyfunction]
    fn x25519_shared_ssl<'py>(
        py: Python<'py>,
        seed: &[u8],
        peer_public: &[u8],
    ) -> PyResult<Bound<'py, PyBytes>> {
        Ok(PyBytes::new(py, &x25519_shared(seed, peer_public)))
    }

    #[pymodule]
    fn opensslport(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(aes_ctr_crypt, m)?)?;
        m.add_function(wrap_pyfunction!(aes_cbc_crypt, m)?)?;
        m.add_function(wrap_pyfunction!(aes_gcm_crypt, m)?)?;
        m.add_function(wrap_pyfunction!(digest_hex_ssl, m)?)?;
        m.add_function(wrap_pyfunction!(rsa_keygen_der, m)?)?;
        m.add_function(wrap_pyfunction!(rand_bytes_ssl, m)?)?;
        m.add_function(wrap_pyfunction!(ed25519_sign_ssl, m)?)?;
        m.add_function(wrap_pyfunction!(ed25519_public_ssl, m)?)?;
        m.add_function(wrap_pyfunction!(ed25519_verify_ssl, m)?)?;
        m.add_function(wrap_pyfunction!(x25519_public_ssl, m)?)?;
        m.add_function(wrap_pyfunction!(x25519_shared_ssl, m)?)?;
        Ok(())
    }
}
