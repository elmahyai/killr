.libPaths(c(
  path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"),
  path.expand("~/R/library"),
  .libPaths()
))
suppressPackageStartupMessages(library(MASS))
if (as.character(packageVersion("MASS")) != "7.3.66") stop("expected MASS 7.3-66")

one <- function() {
  theta <- 2.5
  fam <- neg.bin(theta = theta)
  y <- c(0, 1, 5, 3, 10)
  mu <- c(0.5, 1.2, 4, 3, 8)
  wt <- c(1, 1, 2, 1, 1)
  n <- rep(1, length(y))
  dev <- sum(fam$dev.resids(y, mu, wt))
  eta <- fam$linkfun(mu)
  c(
    as.numeric(fam$variance(mu)),
    fam$dev.resids(y, mu, wt),
    fam$aic(y, n, mu, wt, dev),
    fam$linkfun(mu),
    fam$linkinv(eta),
    fam$mu.eta(eta),
    as.numeric(fam$validmu(mu)),
    as.numeric(fam$validmu(c(1, -1))),
    as.numeric(fam$valideta(eta))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
for (item in value) {
  cat(sprintf("%.17g\n", item))
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
