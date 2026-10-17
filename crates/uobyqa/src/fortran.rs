//! Fortran indexing and `DSIGN`.
//!
//! A Fortran index `J` is `slice[J - 1]`. `DSIGN` copies the sign bit, so a
//! negative zero keeps a negative sign.

#[inline]
pub(crate) fn dsign(magnitude: f64, sign_source: f64) -> f64 {
    magnitude.abs().copysign(sign_source)
}

#[inline]
pub(crate) fn ix(index: i32) -> usize {
    (index - 1) as usize
}

/// Column-major `A(row, col)` with leading dimension `ld`.
#[inline]
pub(crate) fn ix2(ld: i32, row: i32, col: i32) -> usize {
    ((col - 1) * ld + (row - 1)) as usize
}

/// `x**1.5D0` is libm `pow`, the same call gfortran emits.
#[inline]
pub(crate) fn pow15(x: f64) -> f64 {
    x.powf(1.5)
}
