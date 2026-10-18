# Rust trunc is a libm call

`f64::trunc` compiles to a call into libm on the baseline x86-64 target, which has no SSE4.1 round instruction. In the hexbin kernel, `fint` used `value.trunc() as i64` and cost about 58 ns per point. `value as i64` truncates toward zero, maps NaN to 0, and brings the same loop to about 32 ns per point, level with gfortran. For Fortran `INT`, use the `as` cast.
