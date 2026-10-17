.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

## Orthodont with gls(distance ~ age + Sex, weights = varPower()). The default
## covariate is fitted(.), which is not in the data, so R runs its outer repeat
## loop: needUpdate is TRUE and update() re-fits the variance covariate from
## the fitted values each outer step until the convergence test passes.
## The Python side runs nlme.gls.gls on the same fixed data; compare at 1e-8.
data(Orthodont, package = "nlme")

one <- function() {
  fm <- gls(distance ~ age + Sex, Orthodont, weights = varPower())
  c(
    as.numeric(coef(fm)),
    sqrt(diag(fm$varBeta)),
    fm$sigma,
    fm$logLik,
    as.numeric(coef(fm$modelStruct$varStruct)),
    fm$numIter
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
