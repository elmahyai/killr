//! L-BFGS-B as R's `optim(method = "L-BFGS-B")` runs it (R 4.5.0).
//!
//! The port follows `src/appl/lbfgsb.c`, the driver in `src/appl/optim.c`, and
//! the bounded numerical gradient in `src/library/stats/src/optim.c`. The C is
//! vendored in `vendor/`. The pyo3 entry point is `optim_lbfgsb`, behind the
//! default `python` feature.

#![allow(clippy::needless_range_loop)]

mod lbfgsb;

pub use lbfgsb::{optim_lbfgsb, Failure, Output};

#[cfg(feature = "python")]
mod python;
