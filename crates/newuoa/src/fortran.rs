//! 1-based helpers for the fixed-form NEWUOA translation.
//!
//! Fortran index `J` is `slice[J - 1]`. A subroutine that receives `W(IX)`
//! is given `&mut w[ix - 1..]`, so its index 1 is element 0 of that slice.

#[inline]
pub(crate) fn get(a: &[f64], i: i32) -> f64 {
    a[(i - 1) as usize]
}

#[inline]
pub(crate) fn set(a: &mut [f64], i: i32, value: f64) {
    a[(i - 1) as usize] = value;
}

#[inline]
pub(crate) fn get2(a: &[f64], ld: i32, i: i32, j: i32) -> f64 {
    a[((j - 1) * ld + (i - 1)) as usize]
}

#[inline]
pub(crate) fn set2(a: &mut [f64], ld: i32, i: i32, j: i32, value: f64) {
    a[((j - 1) * ld + (i - 1)) as usize] = value;
}

#[inline]
pub(crate) fn dmin1(a: f64, b: f64) -> f64 {
    if a < b {
        a
    } else {
        b
    }
}

#[inline]
pub(crate) fn dmax1(a: f64, b: f64) -> f64 {
    if a > b {
        a
    } else {
        b
    }
}

#[inline]
pub(crate) fn dmax3(a: f64, b: f64, c: f64) -> f64 {
    dmax1(dmax1(a, b), c)
}
