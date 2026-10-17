.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(rootSolve))
logistic <- function (x, times) {
  with(as.list(x), K / (1+(K-N0)/N0*exp(-r*times)))
}
x <- c(N0 = 76.1, r = 0.02, K = 500)
one <- function() as.vector(gradient(logistic, x, times = 0:5))
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
