//! Gower's distance and top-n matches, ported from gower 1.0.2 `src/gower.c`.
//!
//! `kernel` holds the numerical code. `python` (feature `python`) exposes it
//! to Python as the `gower_kernel` module with NumPy arrays.

pub mod kernel;

#[cfg(feature = "python")]
mod python;
