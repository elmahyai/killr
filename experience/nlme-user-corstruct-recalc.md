The generic `recalc.corStruct` calls `logLik`, and `logLik` calls `logDet`, which asks for `corMatrix(corr = FALSE)`. A user class that defines its own `corMatrix` must hand `corr = FALSE` back with `NextMethod()` in R, or the recalc fails inside the user's method even though `corr = TRUE` works.

The factor is `inv(L)` where `mat = L L'`: column `j` solves `L x = e_j`. The added `logLik` is the factor-list log determinant, `-sum(log(diag(L)))`. Proof: `packages/nlme/proof/recalc-generic-r.R`.
