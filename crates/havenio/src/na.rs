//! R's NA payload, from haven `src/tagged_na.c`.
//!
//! On a little-endian host the quiet-NaN words are `1954` then `0x7ff00000`.
//! The tag replaces byte 4.

const NA_BITS: u64 = 0x7ff0_0000_0000_07a2;

pub fn na_real() -> f64 {
    f64::from_bits(NA_BITS)
}

pub fn make_tagged_na(tag: u8) -> f64 {
    let mut bits = NA_BITS;
    if cfg!(target_endian = "little") {
        bits &= !(0xff << 32);
        bits |= (tag as u64) << 32;
    } else {
        bits &= !(0xff << 24);
        bits |= (tag as u64) << 24;
    }
    f64::from_bits(bits)
}

pub fn tagged_na_value(value: f64) -> u8 {
    let bits = value.to_bits();
    if cfg!(target_endian = "little") {
        ((bits >> 32) & 0xff) as u8
    } else {
        ((bits >> 24) & 0xff) as u8
    }
}
