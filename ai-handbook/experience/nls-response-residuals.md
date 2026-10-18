`residuals()` on an `nls` fit is the response residual, left side minus fitted. The residual `nls.lm` minimizes is `sqrt(weights)` times that difference, and deviance is the sum of those squares.
