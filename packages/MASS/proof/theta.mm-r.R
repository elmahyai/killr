.libPaths(c(
  path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"),
  path.expand("~/R/library"),
  .libPaths()
))
suppressPackageStartupMessages(library(MASS))
if (packageDescription("MASS")$Version != "7.3-66") stop("expected MASS 7.3-66")
one <- function() {
  set.seed(42)
  n <- 25L
  x <- rnorm(n)
  y <- rnbinom(n, mu = exp(1 + 0.4 * x), size = 8)
  fit <- glm(y ~ x, family = poisson())
  th <- theta.mm(y, fit$fitted.values, fit$df.residual)
  ml <- theta.ml(y, fit$fitted.values, weights = fit$weights)
  c(as.numeric(th), attr(ml, "SE"))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
for (item in value) cat(sprintf("%.17g\n", item))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
