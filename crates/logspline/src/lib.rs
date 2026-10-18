//! Rust kernels of the R package logspline 2.1.22.
//!
//! `linpack` holds the LINPACK symmetric-indefinite routines used by the Fortran
//! file `src/allpack.f`, with the BLAS calls done inline. `lsdall` holds the
//! oldlogspline fit (`logcensor` in `src/lsdall.c`).

pub mod linpack;
pub mod lsdall;
pub mod nlsd;

#[cfg(feature = "python")]
mod python;
