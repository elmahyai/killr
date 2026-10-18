One `.f` file is not a solver. Link the sources R already combines, and stub `dblepr`, `intpr`, `rexit`, and `rprintf*` when `errmsg.f` expects R.

A single file can be a full solver. pan.f's ECME routines call no R entry point, so the whole file compiles with gfortran and no stubs. For the `zcol = NULL` branch pass a zero-length `q`, not column 0: `prelim` reads `pred(., zcol)` even though nopsi never uses the result.

BLAS is not a crate link either. logspline's `allpack.f` calls BLAS (`DAXPY`, `DDOT`, `DCOPY`, `DSWAP`, `IDAMAX`) beside its LINPACK routines, and BLAS is not in `native.json`. Remake the LINPACK routines in Rust with those calls inlined, keeping the loop order of the Fortran. The result matched R's `.C` output to 1e-12.
