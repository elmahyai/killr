`EQPRO` and `CHOL` are Fortran logicals. The kernels take them as 4-byte integers, `0` or `1`, which is what R `.Fortran` passes for `as.logical`.
