//! Sweep-hull Delaunay triangulation for the R package interp 1.1-6.
//!
//! `tri.mesh` in interp is not tripack. Its triangulation is the s-hull sweep
//! (David Sinclair) in C++, `vendor/s_hull_pro.cpp`, compiled unchanged. The
//! post-processing that builds `trlist`, `cclist`, the arcs and the convex hull
//! is `src/shull_shim.cpp`. Coordinates are float32 inside the sweep, as in R.

mod shull;

#[cfg(feature = "python")]
mod python;

pub use shull::{triangulate, Triangulation};
