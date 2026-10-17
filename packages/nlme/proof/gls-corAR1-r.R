.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

## Oats with gls(yield ~ Variety - 1, correlation = corAR1(form = ~ 1 | Block)).
## R fits the correlation parameter with nlminb (PORT). The Python side runs the
## same PORT kernel (crates/nlminb_port), so these outputs must match at 1e-8.
data(Oats, package = "nlme")
## Block as character: R then sorts groups alphabetically, as the Python side does.
Oats$Block <- as.character(Oats$Block)

one <- function() {
  fm <- gls(yield ~ Variety - 1, Oats, correlation = corAR1(form = ~ 1 | Block))
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
