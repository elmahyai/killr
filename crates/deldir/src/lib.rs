//! Delaunay triangulation and Dirichlet tile kernels, ported from deldir 2.0-4
//! `src/*.f90` (Fortran 90) and `src/init.c`.
//!
//! Copyright (C) Rolf Turner. Licensed under the GNU General Public License,
//! version 2 or later (deldir DESCRIPTION: `GPL (>= 2)`).
//!
//! The entry points called by `deldir()` and `triang.list()` on the default
//! path are `binsrt`, `master`, and `intri`. Other Fortran routines in
//! deldir (`mnnd`, and the `tileArea` caller of `stoke`) are not ported.

pub mod triangulation;

pub use triangulation::{binsrt, intri, master, BinsrtOut, MasterOut, Res};

#[cfg(feature = "python")]
mod python;
