The d > 1 `crit` value is a chi-square sum, not a normal quantile. `scritval` with rdf = 0 solves `2 * sum k0[i] * (1 - pchisq(c^2, d + 1 - i)) / area(d + 1 - i) = 1 - cov`, where `i` runs over the first `min(length(const), d + 1)` constants. Ported as `critval.rs`, it matches R to about 1e-15.

A fit's `critval` for dimension d has const `c(rep(0, d), 1)`. Its only nonzero term uses chi-square with 1 df, so `crit(fit)` is `qnorm(0.975)` = 1.959964 for every d. A const of `c(0, 1)` with d = 2 gives a chi-square with 2 df instead, which is 1.924059.
