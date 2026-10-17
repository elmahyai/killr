//! Isolines, isobands, and clip_lines from isoband 0.3.0 (C++ in `src/isoband.cpp`,
//! `src/polygon.cpp`, and `src/clip-lines.cpp`), as a Rust kernel for the Python package.

mod band_cases;
mod clip;
mod grid;
mod isobands;
mod line_cases;
mod ordered_map;

pub use clip::clip_lines;
pub use grid::Lines;
pub use isobands::{isobands, isolines};

#[cfg(feature = "python")]
mod python;
