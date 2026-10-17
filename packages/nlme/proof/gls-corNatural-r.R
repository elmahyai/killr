.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

## Orthodont with gls(distance ~ age + Sex, correlation = corNatural(form = ~ 1 | Subject)).
## R fits the correlation parameters with nlminb (PORT). The Python side runs the
## same PORT kernel (crates/nlminb_port), so these outputs must match at 1e-8.
data(Orthodont, package = "nlme")
## Subject as character: R then sorts groups alphabetically, as the Python side does.
Orthodont$Subject <- as.character(Orthodont$Subject)

one <- function() {
  fm <- gls(distance ~ age + Sex, Orthodont, correlation = corNatural(form = ~ 1 | Subject))
  c(as.numeric(coef(fm)), sqrt(diag(fm$varBeta)), fm$sigma, fm$logLik)
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
