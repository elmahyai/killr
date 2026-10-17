//! BLAS pieces SUMSL calls: `DDOT` and `DNRM2` from the same libblas R uses.

#[link(name = "blas")]
extern "C" {
    fn ddot_(n: *const i32, x: *const f64, incx: *const i32, y: *const f64, incy: *const i32) -> f64;
    fn dnrm2_(n: *const i32, x: *const f64, incx: *const i32) -> f64;
}

pub fn dot(v: &[f64], n: i32, x: i32, y: i32) -> f64 {
    if n <= 0 {
        return 0.0;
    }
    let inc = 1i32;
    unsafe { ddot_(&n, v.as_ptr().add(x as usize), &inc, v.as_ptr().add(y as usize), &inc) }
}

pub fn nrm2(v: &[f64], n: i32, x: i32) -> f64 {
    if n <= 0 {
        return 0.0;
    }
    let inc = 1i32;
    unsafe { dnrm2_(&n, v.as_ptr().add(x as usize), &inc) }
}

pub fn dmax1(a: f64, b: f64) -> f64 {
    if a >= b { a } else { b }
}

pub fn d1mach(i: i32) -> f64 {
    match i {
        1 => f64::MIN,
        2 => f64::MAX,
        4 => f64::EPSILON,
        _ => 0.0,
    }
}
