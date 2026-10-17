//! One-based indexing into column-major Fortran work arrays.

#[inline(always)]
pub fn g(a: &[f64], i: i32) -> f64 {
    a[(i - 1) as usize]
}

#[inline(always)]
pub fn s(a: &mut [f64], i: i32, v: f64) {
    a[(i - 1) as usize] = v;
}

#[inline(always)]
pub fn g2(a: &[f64], ld: i32, i: i32, j: i32) -> f64 {
    a[(((j - 1) * ld) + (i - 1)) as usize]
}

#[inline(always)]
pub fn s2(a: &mut [f64], ld: i32, i: i32, j: i32, v: f64) {
    a[(((j - 1) * ld) + (i - 1)) as usize] = v;
}

/// Fortran `DMAX1`. Equal values keep the first argument.
#[inline(always)]
pub fn dmax1(a: f64, b: f64) -> f64 {
    if a >= b {
        a
    } else {
        b
    }
}

/// Fortran `DMIN1`. Equal values keep the first argument.
#[inline(always)]
pub fn dmin1(a: f64, b: f64) -> f64 {
    if a <= b {
        a
    } else {
        b
    }
}

#[inline(always)]
pub fn dmax3(a: f64, b: f64, c: f64) -> f64 {
    dmax1(dmax1(a, b), c)
}
