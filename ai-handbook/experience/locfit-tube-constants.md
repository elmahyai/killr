# locfit tube constants (kappa0, geth = 2)

Facts for porting `kappa0`'s `const` (`scb_cons.c` `tube_constants`, `m_isimp.c` `simpson4`), in `crates/locfit/src/kappa0.rs`.

- `simpson4` multiplies only the interior sums (`k0`) by the cell volume. The edge (`l0`) and corner (`m0`) sums are not scaled. So `const = (k0 * vol, l0[0] / 2)` for d = 1, and `const[2] = (k0[2] * vol + l0[1] + m0[0]) / (2 pi)` for d = 2.
- For d = 1, `l1x` returns 1, so `l0[0]` is the endpoint count (2), and `const[2]` is 1. R shows `const = (k0, 1)`.
- The grid uses the data range (`set_flim`) and `sca = 1` (`scale = FALSE`). The grid count is raised to even, which is a no-op for `lfgrid(20)`.
- locfit's `qr` gives a positive R diagonal, so `R11/R00` and `atan2(R22, -R12)` do not depend on row pivoting.
- The crate's Jacobi eigen solve (`eig.rs`, `E_TOL = 1e-8`) makes weight sums exact only to about 1e-8. Use 1e-6 tolerances on derivative-weight tests, not 1e-10.
- `R kappa0()` warns "constants are approximate for varying h" when `alpha > 0`. That is expected output, not an error.
- `crit(const, d = 1)` with a general `const` must call `scritval`, not the normal quantile. Only `const = (0, 1)` at d = 1 takes the quantile.
- `scb()` on its default `ev = lfgrid(20)` calls `locfit.raw` with `geth = 81` (`70 + type + 10 * simul`). That runs the C band path (`scb.c`, `scb_crit.c`, `simul.c`), not only the `kappa0` constants, so `crates/locfit` needs that path before `scb` can match.
