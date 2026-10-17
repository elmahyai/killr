//! Safe wrapper over the C ABI in `src/shull_shim.cpp`.

use std::ffi::CStr;
use std::os::raw::{c_char, c_int};

#[repr(C)]
pub struct ShullResult {
    _private: [u8; 0],
}

unsafe extern "C" {
    fn interp_shull_run(n: c_int, x: *const f64, y: *const f64) -> *mut ShullResult;
    fn interp_shull_free(r: *mut ShullResult);
    fn interp_shull_status(r: *const ShullResult) -> c_int;
    fn interp_shull_error(r: *const ShullResult) -> *const c_char;
    fn interp_shull_nt(r: *const ShullResult) -> c_int;
    fn interp_shull_nch(r: *const ShullResult) -> c_int;
    fn interp_shull_na(r: *const ShullResult) -> c_int;
    fn interp_shull_trlist(r: *const ShullResult) -> *const c_int;
    fn interp_shull_cclist(r: *const ShullResult) -> *const f64;
    fn interp_shull_ch(r: *const ShullResult) -> *const c_int;
    fn interp_shull_a1(r: *const ShullResult) -> *const c_int;
    fn interp_shull_a2(r: *const ShullResult) -> *const c_int;
}

/// Output of `shull.deltri` as interp's C++ returns it.
///
/// `status` is 0 for a triangulation, 1 when interp retries with jitter
/// (`nt` is then -13 or -14, and the other arrays are empty).
/// Indices are 1-based, as in R. `trlist` is row-major, nt x 9;
/// `cclist` is row-major, nt x 5.
#[derive(Debug, Clone, PartialEq)]
pub struct Triangulation {
    pub status: i32,
    pub nt: i32,
    pub trlist: Vec<i32>,
    pub cclist: Vec<f64>,
    pub nch: i32,
    pub ch: Vec<i32>,
    pub na: i32,
    pub a1: Vec<i32>,
    pub a2: Vec<i32>,
}

fn copy_ints(ptr: *const c_int, len: usize) -> Vec<i32> {
    if len == 0 || ptr.is_null() {
        return Vec::new();
    }
    unsafe { std::slice::from_raw_parts(ptr, len).to_vec() }
}

fn copy_doubles(ptr: *const f64, len: usize) -> Vec<f64> {
    if len == 0 || ptr.is_null() {
        return Vec::new();
    }
    unsafe { std::slice::from_raw_parts(ptr, len).to_vec() }
}

/// Triangulate points with the s-hull sweep, as `shull.deltri` does in interp.
///
/// Returns `Err` with the message interp would raise (R `stop`).
pub fn triangulate(x: &[f64], y: &[f64]) -> Result<Triangulation, String> {
    if x.len() != y.len() {
        return Err("length of x and y dont match!".to_string());
    }
    let n = c_int::try_from(x.len()).map_err(|_| "too many points".to_string())?;
    unsafe {
        let r = interp_shull_run(n, x.as_ptr(), y.as_ptr());
        let status = interp_shull_status(r);
        if status == -100 {
            let msg = CStr::from_ptr(interp_shull_error(r)).to_string_lossy().into_owned();
            interp_shull_free(r);
            return Err(msg);
        }
        let out = if status == 1 {
            Triangulation {
                status,
                nt: interp_shull_nt(r),
                trlist: Vec::new(),
                cclist: Vec::new(),
                nch: 0,
                ch: Vec::new(),
                na: 0,
                a1: Vec::new(),
                a2: Vec::new(),
            }
        } else {
            let nt = interp_shull_nt(r);
            let nch = interp_shull_nch(r);
            let na = interp_shull_na(r);
            Triangulation {
                status,
                nt,
                trlist: copy_ints(interp_shull_trlist(r), (nt as usize) * 9),
                cclist: copy_doubles(interp_shull_cclist(r), (nt as usize) * 5),
                nch,
                ch: copy_ints(interp_shull_ch(r), nch as usize),
                na,
                a1: copy_ints(interp_shull_a1(r), na as usize),
                a2: copy_ints(interp_shull_a2(r), na as usize),
            }
        };
        interp_shull_free(r);
        Ok(out)
    }
}
