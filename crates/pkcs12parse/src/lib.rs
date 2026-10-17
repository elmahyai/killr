//! R/openssl `R_parse_pkcs12` and DER normalization from `src/keys.c`.

use foreign_types_shared::ForeignTypeRef;
use openssl::pkcs12::Pkcs12;
use openssl::pkey::PKey;
use openssl::x509::X509;
use std::ffi::CStr;
use std::os::raw::{c_long, c_void};
use std::sync::Once;

fn ensure_legacy() {
    static ONCE: Once = Once::new();
    ONCE.call_once(|| {
        if let Ok(provider) = openssl::provider::Provider::try_load(None, "legacy", true) {
            std::mem::forget(provider);
        }
    });
}

fn normalize_cert_der(input: &[u8]) -> Result<Vec<u8>, openssl::error::ErrorStack> {
    X509::from_der(input)?.to_der()
}

fn normalize_key_der(input: &[u8]) -> Result<Vec<u8>, openssl::error::ErrorStack> {
    PKey::private_key_from_der(input)?.private_key_to_der()
}

fn normalize_pubkey_der(input: &[u8]) -> Result<Vec<u8>, openssl::error::ErrorStack> {
    PKey::public_key_from_der(input)?.public_key_to_der()
}

fn derive_pubkey_der(input: &[u8]) -> Result<Vec<u8>, openssl::error::ErrorStack> {
    PKey::private_key_from_der(input)?.public_key_to_der()
}

fn cert_pubkey_der(input: &[u8]) -> Result<Vec<u8>, openssl::error::ErrorStack> {
    let cert = X509::from_der(input)?;
    cert.public_key()?.public_key_to_der()
}

fn mac_ok_without_password(p12: &openssl::pkcs12::Pkcs12Ref) -> bool {
    unsafe {
        use pkcs12_ffi::PKCS12_verify_mac;
        let ptr = p12.as_ptr() as *mut c_void;
        PKCS12_verify_mac(ptr, std::ptr::null(), 0) == 1
            || PKCS12_verify_mac(ptr, b"\0".as_ptr() as *const i8, 1) == 1
    }
}

fn parse_pkcs12_inner(data: &[u8], password: Option<&str>) -> Result<ParsedParts, ParseError> {
    ensure_legacy();
    let p12 = Pkcs12::from_der(data).map_err(|_| ParseError::InvalidP12)?;
    let parsed = if mac_ok_without_password(&p12) {
        p12.parse2("").map_err(map_parse_err)?
    } else {
        let pass = password.ok_or(ParseError::NeedPassword)?;
        p12.parse2(pass).map_err(|err| {
            if err.to_string().contains("mac verify failure") {
                ParseError::InvalidPassword
            } else {
                ParseError::OpenSsl(err.to_string())
            }
        })?
    };
    let name = find_friendly_name(data);
    let mut ca = Vec::new();
    if let Some(stack) = parsed.ca.as_ref() {
        for cert in stack.iter() {
            ca.push(
                cert.to_der()
                    .map_err(|err| ParseError::OpenSsl(err.to_string()))?,
            );
        }
    }
    Ok(ParsedParts {
        cert: parsed
            .cert
            .map(|c| c.to_der())
            .transpose()
            .map_err(|err| ParseError::OpenSsl(err.to_string()))?,
        key: parsed
            .pkey
            .map(|k| k.private_key_to_der())
            .transpose()
            .map_err(|err| ParseError::OpenSsl(err.to_string()))?,
        ca,
        name,
    })
}

fn map_parse_err(err: openssl::error::ErrorStack) -> ParseError {
    if err.to_string().contains("mac verify failure") {
        ParseError::InvalidPassword
    } else {
        ParseError::OpenSsl(err.to_string())
    }
}

struct ParsedParts {
    cert: Option<Vec<u8>>,
    key: Option<Vec<u8>>,
    ca: Vec<Vec<u8>>,
    name: Option<String>,
}

#[derive(Debug)]
enum ParseError {
    InvalidP12,
    NeedPassword,
    InvalidPassword,
    OpenSsl(String),
}

impl ParseError {
    fn message(&self) -> String {
        match self {
            ParseError::InvalidPassword | ParseError::NeedPassword => {
                "PKCS12 read failure: invalid password".into()
            }
            ParseError::InvalidP12 => "PKCS12 read failure".into(),
            ParseError::OpenSsl(msg) => msg.clone(),
        }
    }
}

mod pkcs12_ffi {
    use std::os::raw::{c_char, c_int, c_long, c_void};

    type STACK = c_void;
    type PKCS7 = c_void;
    type PKCS12_SAFEBAG = c_void;
    type ASN1_OBJECT = c_void;

    #[link(name = "crypto")]
    extern "C" {
        pub fn d2i_PKCS12(
            a: *mut *mut c_void,
            pp: *mut *const u8,
            length: c_long,
        ) -> *mut c_void;
        pub fn PKCS12_free(p12: *mut c_void);
        pub fn PKCS12_verify_mac(
            p12: *mut c_void,
            pass: *const c_char,
            passlen: c_int,
        ) -> c_int;
        pub fn PKCS12_unpack_authsafes(p12: *mut c_void) -> *mut STACK;
        pub fn PKCS12_unpack_p7data(p7: *const PKCS7) -> *mut STACK;
        pub fn PKCS12_get_friendlyname(bag: *mut PKCS12_SAFEBAG) -> *mut c_char;
        pub fn OBJ_obj2nid(o: *const ASN1_OBJECT) -> c_int;
        pub fn OPENSSL_sk_num(st: *const STACK) -> c_int;
        pub fn OPENSSL_sk_value(st: *const STACK, idx: c_int) -> *mut c_void;
        pub fn OPENSSL_sk_free(st: *mut STACK);
    }

    pub const NID_pkcs7_data: c_int = 21;
}

fn find_friendly_name(data: &[u8]) -> Option<String> {
    use pkcs12_ffi::*;
    unsafe {
        let mut ptr = data.as_ptr();
        let p12 = d2i_PKCS12(std::ptr::null_mut(), &mut ptr, data.len() as c_long);
        if p12.is_null() {
            return None;
        }
        let safes = PKCS12_unpack_authsafes(p12);
        if safes.is_null() {
            PKCS12_free(p12);
            return None;
        }
        let mut found: Option<String> = None;
        let n = OPENSSL_sk_num(safes);
        for idx in 0..n {
            if found.is_some() {
                break;
            }
            let safe = OPENSSL_sk_value(safes, idx) as *mut c_void;
            if safe.is_null() {
                continue;
            }
            let type_ptr = safe as *const u8;
            // PKCS7.type is first field (ASN1_OBJECT*).
            let type_obj = *(type_ptr as *const *const c_void);
            if OBJ_obj2nid(type_obj) != NID_pkcs7_data {
                continue;
            }
            let bags = PKCS12_unpack_p7data(safe);
            if bags.is_null() {
                continue;
            }
            let m = OPENSSL_sk_num(bags);
            for bag_idx in 0..m {
                if found.is_some() {
                    break;
                }
                let bag = OPENSSL_sk_value(bags, bag_idx) as *mut c_void;
                if bag.is_null() {
                    continue;
                }
                let c_name = PKCS12_get_friendlyname(bag);
                if !c_name.is_null() {
                    found = CStr::from_ptr(c_name).to_str().ok().map(str::to_owned);
                }
            }
            OPENSSL_sk_free(bags);
        }
        OPENSSL_sk_free(safes);
        PKCS12_free(p12);
        found
    }
}

#[cfg(feature = "python")]
mod python {
    use super::{
        cert_pubkey_der, derive_pubkey_der, normalize_cert_der, normalize_key_der,
        normalize_pubkey_der, parse_pkcs12_inner, ParseError,
    };
    use pyo3::exceptions::PyRuntimeError;
    use pyo3::prelude::*;
    use pyo3::types::{PyBytes, PyList, PyTuple};

    fn map_err(err: ParseError) -> PyErr {
        PyRuntimeError::new_err(err.message())
    }

    #[pyfunction]
    #[pyo3(signature = (data, password=None))]
    fn parse_pkcs12<'py>(
        py: Python<'py>,
        data: &[u8],
        password: Option<&str>,
    ) -> PyResult<Bound<'py, PyTuple>> {
        let parts = parse_pkcs12_inner(data, password).map_err(map_err)?;
        let cert = match parts.cert {
            Some(raw) => PyBytes::new(py, &raw).into_any().unbind(),
            None => py.None().into(),
        };
        let key = match parts.key {
            Some(raw) => PyBytes::new(py, &raw).into_any().unbind(),
            None => py.None().into(),
        };
        let ca = PyList::empty(py);
        for item in parts.ca {
            ca.append(PyBytes::new(py, &item))?;
        }
        let name = match parts.name {
            Some(text) => text.into_pyobject(py)?.into_any().unbind(),
            None => py.None().into(),
        };
        Ok(PyTuple::new(py, [cert, key, ca.into_any().unbind(), name])?)
    }

    #[pyfunction]
    fn parse_der_cert<'py>(py: Python<'py>, data: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
        let out =
            normalize_cert_der(data).map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        Ok(PyBytes::new(py, &out))
    }

    #[pyfunction]
    fn parse_der_key<'py>(py: Python<'py>, data: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
        let out =
            normalize_key_der(data).map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        Ok(PyBytes::new(py, &out))
    }

    #[pyfunction]
    fn parse_der_pubkey<'py>(py: Python<'py>, data: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
        let out =
            normalize_pubkey_der(data).map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        Ok(PyBytes::new(py, &out))
    }

    #[pyfunction]
    fn derive_pubkey<'py>(py: Python<'py>, data: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
        let out = derive_pubkey_der(data).map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        Ok(PyBytes::new(py, &out))
    }

    #[pyfunction]
    fn cert_pubkey<'py>(py: Python<'py>, data: &[u8]) -> PyResult<Bound<'py, PyBytes>> {
        let out = cert_pubkey_der(data).map_err(|err| PyRuntimeError::new_err(err.to_string()))?;
        Ok(PyBytes::new(py, &out))
    }

    #[pymodule]
    fn pkcs12parse(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(parse_pkcs12, m)?)?;
        m.add_function(wrap_pyfunction!(parse_der_cert, m)?)?;
        m.add_function(wrap_pyfunction!(parse_der_key, m)?)?;
        m.add_function(wrap_pyfunction!(parse_der_pubkey, m)?)?;
        m.add_function(wrap_pyfunction!(derive_pubkey, m)?)?;
        m.add_function(wrap_pyfunction!(cert_pubkey, m)?)?;
        Ok(())
    }
}
