# Locfit density normalization

For `density.lf` with link `ident` and degree 0, the fit at grid point g is `sum_i W(|x_i - g| / h) / (n * h * int W)`. The `n` factor is needed: without it the values are n times too large.

For the Gaussian window, `int W` is over the whole line, `sqrt(2 pi) / 2.5`, not over `[-h, h]`. locfit's integration ignores the limits for Gaussian weights. For compact kernels, the integral is over the support `[-1, 1]` in scaled units.

The default window is Gaussian with `h = width / 2 * 1.25` and `cut = 0.75`. Other windows use `cut = 0.5`.
