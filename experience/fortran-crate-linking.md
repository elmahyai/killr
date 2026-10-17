One `.f` file is not a solver. Link the sources R already combines, and stub `dblepr`, `intpr`, `rexit`, and `rprintf*` when `errmsg.f` expects R.

A single file can be a full solver. pan.f's ECME routines call no R entry point, so the whole file compiles with gfortran and no stubs. For the `zcol = NULL` branch pass a zero-length `q`, not column 0: `prelim` reads `pred(., zcol)` even though nopsi never uses the result.
