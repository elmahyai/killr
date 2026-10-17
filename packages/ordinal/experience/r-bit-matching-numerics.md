# Bit-matching R numerics for optimizers

When an optimizer uses finite-difference gradients (nlminb/PORT here), last-bit differences in the objective or the start vector grow into 1e-7 to 1e-6 differences in the fit. Matching R within 1e-8 needs the same arithmetic, not just the same formula.

Things that mattered for `clmm`:

- `B %*% v` goes through dgemv in the system BLAS that R uses. A hand-written loop differs in the last bits.
- `sum(log(x))` accumulates in long double in R. Use long double in C for the sum.
- R 4.5 `R_pow_di` uses repeated squaring and takes the reciprocal at the end for negative n.
- `gauss.hermite` nodes and weights come from `eigen(..., symmetric = TRUE)`, which is LAPACK dsyevr. numpy `eigh` is not bit-identical, and the nAGQ=10 gradient missed 1e-8 because of it.
- Fix the start vector in both R and Python proofs when the default start differs by about 1e-15.
