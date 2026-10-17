.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(ucminf))

one <- function() {
  fR <- function(x) (1 - x[1])^2 + 100 * (x[2] - x[1]^2)^2
  gR <- function(x) c(-400 * x[1] * (x[2] - x[1] * x[1]) - 2 * (1 - x[1]),
                      200 * (x[2] - x[1] * x[1]))
  fit <- ucminf(par = c(2, 0.5), fn = fR, gr = gR)
  as.numeric(c(fit$par, fit$value, fit$convergence, fit$info, fit$invhessian.lt))
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
