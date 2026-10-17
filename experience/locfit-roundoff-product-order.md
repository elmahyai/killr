# Locfit roundoff product order

Weighted locfit fits (`locfit.quasi`, `locfit.robust`) iterate, and the
two-dimensional default tree amplifies roundoff. A 1e-15 relative change in `y`
moves the vertex table by about 1e-7. The miss to R came from the grouping of
products, not from the Jacobi rule.

- Keep R's Jacobi stop, `x^2 > 1e-15 * |x_ii x_jj|`. Other thresholds move the
  result by 1e-5 or more, so the rule is correct and must not be relaxed.
- Group the products as the C does. `reginit`: `s1 += K * (pw * y)`. `likereg`:
  `f1 += (X * K) * (pw * z)`, and `addouter` with `c = K * pw` then `(c * X_i) * X_j`.
- One dimension uses `rho = fabs(x / sc)`, not `sqrt(x^2)`, which can differ by an ulp.

With these, `locfit.quasi` and `locfit.robust` match R at 5e-14 for d = 1 and d = 2.
