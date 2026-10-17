.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(rootSolve))

g <- function(t, y, p) {
  n <- length(y)
  dy <- numeric(n)
  dy[1] <- y[2] - y[1]
  for (i in 2:(n - 1)) dy[i] <- y[i - 1] - 2 * y[i] + y[i + 1]
  dy[n] <- 1 - y[n]
  list(dy)
}
f <- function(x) g(0, x, NULL)[[1]]
one <- function() {
multiroot.1D(f, rep(0.2, 5), nspec = 1)$root
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
