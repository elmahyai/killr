//! OpenSSH fingerprint wire bytes (R/openssl `fpdata` + `openssh.c` bignum padding).

use openssl::bn::{BigNum, BigNumRef};
use openssl::pkey::{Id, PKey, Public};
use openssl::rsa::Rsa;
use openssl::dsa::Dsa;
use openssl::ec::EcKeyRef;

fn ssh_string(buf: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(4 + buf.len());
    let len = u32::try_from(buf.len()).expect("ssh string length");
    out.extend_from_slice(&len.to_be_bytes());
    out.extend_from_slice(buf);
    out
}

fn wire_parts(parts: &[&[u8]]) -> Vec<u8> {
    let mut out = Vec::new();
    for part in parts {
        out.extend_from_slice(&ssh_string(part));
    }
    out
}

/// Match `bignum_to_r` / `bignum_to_r_size` in openssh.c (leading zero padding).
fn bignum_padded(bn: &BigNumRef, fixed: Option<usize>) -> Vec<u8> {
    let nbytes = fixed.unwrap_or((bn.num_bits() as usize / 8) + 1);
    let raw = bn.to_vec();
    let mut out = vec![0u8; nbytes];
    let start = nbytes.saturating_sub(raw.len());
    out[start..].copy_from_slice(&raw);
    out
}

fn nid_keysize(nid: openssl::nid::Nid) -> usize {
    use openssl::nid::Nid;
    match nid {
        Nid::X9_62_PRIME256V1 => 32,
        Nid::SECP384R1 => 48,
        Nid::SECP521R1 => 66,
        _ => 0,
    }
}

fn nid_to_nist(nid: openssl::nid::Nid) -> Option<&'static str> {
    use openssl::nid::Nid;
    match nid {
        Nid::X9_62_PRIME256V1 => Some("P-256"),
        Nid::SECP384R1 => Some("P-384"),
        Nid::SECP521R1 => Some("P-521"),
        _ => None,
    }
}

fn nist_to_ssh(nist: &str) -> Option<&'static str> {
    match nist {
        "P-256" => Some("nistp256"),
        "P-384" => Some("nistp384"),
        "P-521" => Some("nistp521"),
        _ => None,
    }
}

fn fpdata_rsa(rsa: &Rsa<Public>) -> Vec<u8> {
    let e = rsa.e();
    let n = rsa.n();
    let e_bytes = bignum_padded(e, None);
    let n_bytes = bignum_padded(n, None);
    let parts = [b"ssh-rsa".as_slice(), e_bytes.as_slice(), n_bytes.as_slice()];
    wire_parts(&parts)
}

fn fpdata_dsa(dsa: &Dsa<Public>) -> Vec<u8> {
    let p_bytes = bignum_padded(dsa.p(), None);
    let q_bytes = bignum_padded(dsa.q(), None);
    let g_bytes = bignum_padded(dsa.g(), None);
    let y_bytes = bignum_padded(dsa.pub_key(), None);
    wire_parts(&[
        b"ssh-dss",
        p_bytes.as_slice(),
        q_bytes.as_slice(),
        g_bytes.as_slice(),
        y_bytes.as_slice(),
    ])
}

fn fpdata_ec(ec: &EcKeyRef<Public>) -> Vec<u8> {
    let group = ec.group();
    let nid = group.curve_name().expect("curve name");
    let nist = nid_to_nist(nid).expect("nist curve");
    let ssh_name = nist_to_ssh(nist).expect("ssh curve name");
    let keysize = nid_keysize(nid);
    let mut x = BigNum::new().expect("bn x");
    let mut y = BigNum::new().expect("bn y");
    let mut ctx = openssl::bn::BigNumContext::new().expect("bn ctx");
    ec.public_key()
        .affine_coordinates_gfp(group, &mut x, &mut y, &mut ctx)
        .expect("ec affine");
    let mut keydata = vec![4u8];
    keydata.extend_from_slice(&bignum_padded(&x, Some(keysize)));
    keydata.extend_from_slice(&bignum_padded(&y, Some(keysize)));
    let header = format!("ecdsa-sha2-{ssh_name}");
    wire_parts(&[
        header.as_bytes(),
        ssh_name.as_bytes(),
        keydata.as_slice(),
    ])
}

fn fpdata_ed25519_raw(raw: &[u8]) -> Vec<u8> {
    wire_parts(&[b"ssh-ed25519", raw])
}

fn fpdata_x25519_raw(raw: &[u8]) -> Vec<u8> {
    wire_parts(&[b"ssh-x25519", raw])
}

fn fpdata_public_pkey(pkey: &PKey<Public>) -> Vec<u8> {
    match pkey.id() {
        Id::RSA => fpdata_rsa(&pkey.rsa().expect("rsa")),
        Id::DSA => fpdata_dsa(&pkey.dsa().expect("dsa")),
        Id::EC => fpdata_ec(&pkey.ec_key().expect("ec")),
        Id::ED25519 => {
            let raw = pkey.raw_public_key().expect("ed25519 raw");
            fpdata_ed25519_raw(&raw)
        }
        Id::X25519 => {
            let raw = pkey.raw_public_key().expect("x25519 raw");
            fpdata_x25519_raw(&raw)
        }
        _ => panic!("unsupported key type for OpenSSH fingerprint"),
    }
}

/// DER SPKI public key bytes to OpenSSH wire data (before hashing).
pub fn fpdata_from_pubkey_der(der: &[u8]) -> Vec<u8> {
    let pkey = PKey::public_key_from_der(der).expect("public key der");
    fpdata_public_pkey(&pkey)
}

/// DER private key to DER public key (R `derive_pubkey`).
pub fn derive_pubkey_der(priv_der: &[u8]) -> Vec<u8> {
    let pkey = PKey::private_key_from_der(priv_der).expect("private key der");
    pkey.public_key_to_der().expect("public key der")
}

/// Wire bytes for a 32-byte Ed25519 public key (no DER wrapper).
pub fn fpdata_ed25519_public_raw(raw: &[u8]) -> Vec<u8> {
    fpdata_ed25519_raw(raw)
}

/// Wire bytes for a 32-byte X25519 public key (no DER wrapper).
pub fn fpdata_x25519_public_raw(raw: &[u8]) -> Vec<u8> {
    fpdata_x25519_raw(raw)
}

/// OpenSSH wire data from a private or public DER key.
pub fn fpdata_from_key_der(der: &[u8]) -> Vec<u8> {
    if let Ok(pkey) = PKey::public_key_from_der(der) {
        return fpdata_public_pkey(&pkey);
    }
    let pub_der = derive_pubkey_der(der);
    fpdata_from_pubkey_der(&pub_der)
}

#[cfg(feature = "python")]
mod python {
    use super::{
        derive_pubkey_der, fpdata_ed25519_public_raw, fpdata_from_key_der, fpdata_from_pubkey_der,
        fpdata_x25519_public_raw,
    };
    use pyo3::prelude::*;

    #[pyfunction]
    fn fpdata_key(der: &[u8]) -> Vec<u8> {
        fpdata_from_key_der(der)
    }

    #[pyfunction]
    fn fpdata_pubkey(der: &[u8]) -> Vec<u8> {
        fpdata_from_pubkey_der(der)
    }

    #[pyfunction]
    fn derive_pubkey(der: &[u8]) -> Vec<u8> {
        derive_pubkey_der(der)
    }

    #[pyfunction]
    fn fpdata_ed25519(raw: &[u8]) -> Vec<u8> {
        fpdata_ed25519_public_raw(raw)
    }

    #[pyfunction]
    fn fpdata_x25519(raw: &[u8]) -> Vec<u8> {
        fpdata_x25519_public_raw(raw)
    }

    #[pymodule]
    fn opensshfp(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(fpdata_key, m)?)?;
        m.add_function(wrap_pyfunction!(fpdata_pubkey, m)?)?;
        m.add_function(wrap_pyfunction!(derive_pubkey, m)?)?;
        m.add_function(wrap_pyfunction!(fpdata_ed25519, m)?)?;
        m.add_function(wrap_pyfunction!(fpdata_x25519, m)?)?;
        Ok(())
    }
}
