//! R/openssl `read_pubkey` parsing (pem.c, keys.c, ssh2.R wire format).

use openssl::bn::BigNum;
use openssl::dsa::Dsa;
use openssl::ec::{EcGroup, EcKey};
use openssl::nid::Nid;
use openssl::pkey::{Id, PKey};
use openssl::rsa::Rsa;
use openssl::x509::X509;
use std::io::{Cursor, Read};

pub fn parse_der_pubkey(input: &[u8]) -> Result<Vec<u8>, String> {
    let pkey = PKey::public_key_from_der(input).map_err(|e| e.to_string())?;
    pkey.public_key_to_der().map_err(|e| e.to_string())
}

pub fn parse_pem_pubkey(input: &[u8]) -> Result<Vec<u8>, String> {
    let pkey = PKey::public_key_from_pem(input).map_err(|e| e.to_string())?;
    pkey.public_key_to_der().map_err(|e| e.to_string())
}

pub fn parse_legacy_pubkey(input: &[u8]) -> Result<Vec<u8>, String> {
    let rsa = Rsa::public_key_from_pem(input).map_err(|e| e.to_string())?;
    let pkey = PKey::from_rsa(rsa).map_err(|e| e.to_string())?;
    pkey.public_key_to_der().map_err(|e| e.to_string())
}

pub fn parse_pem_key(input: &[u8], password: Option<&str>) -> Result<Vec<u8>, String> {
    let cb = password.map(|p| p.as_bytes());
    let pkey = if let Some(pass) = cb {
        PKey::private_key_from_pem_passphrase(input, pass).map_err(|e| e.to_string())?
    } else {
        PKey::private_key_from_pem(input).map_err(|e| e.to_string())?
    };
    pkey.private_key_to_der().map_err(|e| e.to_string())
}

pub fn parse_pem_cert(input: &[u8]) -> Result<Vec<u8>, String> {
    let cert = X509::from_pem(input).map_err(|e| e.to_string())?;
    cert.to_der().map_err(|e| e.to_string())
}

pub fn derive_pubkey_der(priv_der: &[u8]) -> Result<Vec<u8>, String> {
    let pkey = PKey::private_key_from_der(priv_der).map_err(|e| e.to_string())?;
    pkey.public_key_to_der().map_err(|e| e.to_string())
}

pub fn cert_pubkey_der(cert_der: &[u8]) -> Result<Vec<u8>, String> {
    let cert = X509::from_der(cert_der).map_err(|e| e.to_string())?;
    let pkey = cert.public_key().map_err(|e| e.to_string())?;
    pkey.public_key_to_der().map_err(|e| e.to_string())
}

pub fn pubkey_type(der: &[u8]) -> Result<String, String> {
    let pkey = PKey::public_key_from_der(der).map_err(|e| e.to_string())?;
    Ok(match pkey.id() {
        Id::RSA => "rsa".into(),
        Id::DSA => "dsa".into(),
        Id::EC => "ecdsa".into(),
        Id::ED25519 => "ed25519".into(),
        Id::X25519 => "x25519".into(),
        other => return Err(format!("Unsupported key type: {:?}", other)),
    })
}

fn read_ssh_string(cursor: &mut Cursor<&[u8]>) -> Result<Vec<u8>, String> {
    let mut len_buf = [0u8; 4];
    cursor
        .read_exact(&mut len_buf)
        .map_err(|_| "unexpected EOF".to_string())?;
    let size = u32::from_be_bytes(len_buf) as usize;
    if size == 0 {
        return Ok(Vec::new());
    }
    let mut buf = vec![0u8; size];
    let n = cursor.read(&mut buf).map_err(|e| e.to_string())?;
    if n < size {
        // R padding_start trick for OpenSSH private key blobs
        if size == 16909060 && buf.len() >= 4 {
            let expected: Vec<u8> = (1..=buf.len()).map(|i| (i + 4) as u8).collect();
            if buf == expected {
                return Ok(Vec::new());
            }
        }
        return Err("Trailing trash found in buffer".to_string());
    }
    Ok(buf)
}

fn ssh_parse_data(data: &[u8]) -> Result<Vec<Vec<u8>>, String> {
    let mut cursor = Cursor::new(data);
    let mut out = Vec::new();
    loop {
        match read_ssh_string(&mut cursor) {
            Err(e) if e == "unexpected EOF" => break,
            Err(e) => return Err(e),
            Ok(buf) => {
                if buf.is_empty() && cursor.position() as usize >= data.len() {
                    break;
                }
                out.push(buf);
                if cursor.position() as usize >= data.len() {
                    break;
                }
            }
        }
    }
    Ok(out)
}

fn bn_from_slice(raw: &[u8]) -> Result<BigNum, String> {
    BigNum::from_slice(raw).map_err(|e| e.to_string())
}

fn rsa_pubkey_from_parts(exp: &[u8], modulus: &[u8]) -> Result<Vec<u8>, String> {
    let e = bn_from_slice(exp)?;
    let n = bn_from_slice(modulus)?;
    let rsa = Rsa::from_public_components(n, e).map_err(|e| e.to_string())?;
    let pkey = PKey::from_rsa(rsa).map_err(|e| e.to_string())?;
    pkey.public_key_to_der().map_err(|e| e.to_string())
}

fn dsa_pubkey_from_parts(p: &[u8], q: &[u8], g: &[u8], y: &[u8]) -> Result<Vec<u8>, String> {
    let p = bn_from_slice(p)?;
    let q = bn_from_slice(q)?;
    let g = bn_from_slice(g)?;
    let y = bn_from_slice(y)?;
    let dsa = Dsa::from_public_components(p, q, g, y).map_err(|e| e.to_string())?;
    let pkey = PKey::from_dsa(dsa).map_err(|e| e.to_string())?;
    pkey.public_key_to_der().map_err(|e| e.to_string())
}

fn nist_from_ssh(name: &str) -> Result<Nid, String> {
    match name {
        "nistp256" => Ok(Nid::X9_62_PRIME256V1),
        "nistp384" => Ok(Nid::SECP384R1),
        "nistp521" => Ok(Nid::SECP521R1),
        _ => Err(format!("Unsupported curve type: {name}")),
    }
}

fn ecdsa_pubkey_from_ssh(curve_name: &str, ec_point: &[u8]) -> Result<Vec<u8>, String> {
    if ec_point.first() != Some(&4) {
        return Err("Invalid ecdsa format (not uncompressed?)".into());
    }
    let coords = &ec_point[1..];
    let curve_size = coords.len() / 2;
    let x_raw = &coords[..curve_size];
    let y_raw = &coords[curve_size..];
    let nid = nist_from_ssh(curve_name)?;
    let group = EcGroup::from_curve_name(nid).map_err(|e| e.to_string())?;
    let x = bn_from_slice(x_raw)?;
    let y = bn_from_slice(y_raw)?;
    let ec = EcKey::from_public_key_affine_coordinates(&group, &x, &y)
        .map_err(|e| e.to_string())?;
    let pkey = PKey::from_ec_key(ec).map_err(|e| e.to_string())?;
    pkey.public_key_to_der().map_err(|e| e.to_string())
}

fn ed25519_pubkey_from_raw(raw: &[u8]) -> Result<Vec<u8>, String> {
    let pkey = PKey::public_key_from_raw_bytes(raw, Id::ED25519).map_err(|e| e.to_string())?;
    pkey.public_key_to_der().map_err(|e| e.to_string())
}

pub fn ssh_build_pubkey(keydata: &[u8]) -> Result<Vec<u8>, String> {
    let parts = ssh_parse_data(keydata)?;
    if parts.is_empty() {
        return Err("empty ssh key".into());
    }
    let header = std::str::from_utf8(&parts[0]).map_err(|e| e.to_string())?;
    match header {
        "ssh-rsa" => {
            if parts.len() < 3 {
                return Err("invalid ssh-rsa key".into());
            }
            rsa_pubkey_from_parts(&parts[1], &parts[2])
        }
        "ssh-dss" => {
            if parts.len() < 5 {
                return Err("invalid ssh-dss key".into());
            }
            dsa_pubkey_from_parts(&parts[1], &parts[2], &parts[3], &parts[4])
        }
        "ssh-ed25519" => {
            if parts.len() < 2 {
                return Err("invalid ssh-ed25519 key".into());
            }
            ed25519_pubkey_from_raw(&parts[1])
        }
        "ecdsa-sha2-nistp256" | "ecdsa-sha2-nistp384" | "ecdsa-sha2-nistp521" => {
            if parts.len() < 3 {
                return Err("invalid ecdsa ssh key".into());
            }
            let curve = std::str::from_utf8(&parts[1]).map_err(|e| e.to_string())?;
            ecdsa_pubkey_from_ssh(curve, &parts[2])
        }
        _ => Err(format!("Unsupported keytype: {header}")),
    }
}

pub fn openssh_key_first_pubkey(data: &[u8]) -> Result<Vec<u8>, String> {
    let mut cursor = Cursor::new(data);
    let mut magic = Vec::new();
    loop {
        let mut byte = [0u8; 1];
        if cursor.read_exact(&mut byte).is_err() {
            return Err("invalid openssh key blob".into());
        }
        if byte[0] == 0 {
            break;
        }
        magic.push(byte[0]);
    }
    if magic != b"openssh-key-v1" {
        return Err("invalid openssh key magic".into());
    }
    let _ciphername = read_ssh_string(&mut cursor)?;
    let _kdfname = read_ssh_string(&mut cursor)?;
    let _kdfoptions = read_ssh_string(&mut cursor)?;
    let mut count_buf = [0u8; 4];
    cursor
        .read_exact(&mut count_buf)
        .map_err(|e| e.to_string())?;
    let count = u32::from_be_bytes(count_buf) as usize;
    let mut first_pub = None;
    for _ in 0..count {
        let buf = read_ssh_string(&mut cursor)?;
        if first_pub.is_none() {
            first_pub = Some(buf);
        }
    }
    let pubdata = first_pub.ok_or_else(|| "no public key in openssh private key".to_string())?;
    ssh_build_pubkey(&pubdata)
}

#[cfg(feature = "python")]
mod python {
    use super::*;
    use pyo3::prelude::*;

    #[pyfunction]
    fn parse_der_pubkey_py(input: &[u8]) -> PyResult<Vec<u8>> {
        parse_der_pubkey(input).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
    }

    #[pyfunction]
    fn parse_pem_pubkey_py(input: &[u8]) -> PyResult<Vec<u8>> {
        parse_pem_pubkey(input).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
    }

    #[pyfunction]
    fn parse_legacy_pubkey_py(input: &[u8]) -> PyResult<Vec<u8>> {
        parse_legacy_pubkey(input).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
    }

    #[pyfunction]
    #[pyo3(signature = (input, password=None))]
    fn parse_pem_key_py(input: &[u8], password: Option<&str>) -> PyResult<Vec<u8>> {
        parse_pem_key(input, password).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
    }

    #[pyfunction]
    fn parse_pem_cert_py(input: &[u8]) -> PyResult<Vec<u8>> {
        parse_pem_cert(input).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
    }

    #[pyfunction]
    fn derive_pubkey_py(input: &[u8]) -> PyResult<Vec<u8>> {
        derive_pubkey_der(input).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
    }

    #[pyfunction]
    fn cert_pubkey_py(input: &[u8]) -> PyResult<Vec<u8>> {
        cert_pubkey_der(input).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
    }

    #[pyfunction]
    fn pubkey_type_py(input: &[u8]) -> PyResult<String> {
        pubkey_type(input).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
    }

    #[pyfunction]
    fn ssh_build_pubkey_py(input: &[u8]) -> PyResult<Vec<u8>> {
        ssh_build_pubkey(input).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
    }

    #[pyfunction]
    fn openssh_key_pubkey_py(input: &[u8]) -> PyResult<Vec<u8>> {
        openssh_key_first_pubkey(input).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
    }

    #[pyfunction]
    fn ed25519_pubkey_der_py(raw: &[u8]) -> PyResult<Vec<u8>> {
        ed25519_pubkey_from_raw(raw).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e))
    }

    #[pyfunction]
    fn x25519_pubkey_der_py(raw: &[u8]) -> PyResult<Vec<u8>> {
        let pkey =
            PKey::public_key_from_raw_bytes(raw, Id::X25519).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        pkey.public_key_to_der()
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
    }

    #[pymodule]
    fn readpubkey(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(parse_der_pubkey_py, m)?)?;
        m.add_function(wrap_pyfunction!(parse_pem_pubkey_py, m)?)?;
        m.add_function(wrap_pyfunction!(parse_legacy_pubkey_py, m)?)?;
        m.add_function(wrap_pyfunction!(parse_pem_key_py, m)?)?;
        m.add_function(wrap_pyfunction!(parse_pem_cert_py, m)?)?;
        m.add_function(wrap_pyfunction!(derive_pubkey_py, m)?)?;
        m.add_function(wrap_pyfunction!(cert_pubkey_py, m)?)?;
        m.add_function(wrap_pyfunction!(pubkey_type_py, m)?)?;
        m.add_function(wrap_pyfunction!(ssh_build_pubkey_py, m)?)?;
        m.add_function(wrap_pyfunction!(openssh_key_pubkey_py, m)?)?;
        m.add_function(wrap_pyfunction!(ed25519_pubkey_der_py, m)?)?;
        m.add_function(wrap_pyfunction!(x25519_pubkey_der_py, m)?)?;
        Ok(())
    }
}
