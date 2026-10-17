.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
f <- function(t, y, parms) {
  dy1 <- -0.04 * y[1] + 1e4 * y[2] * y[3]
  dy2 <- 0.04 * y[1] - 1e4 * y[2] * y[3] - 3e7 * y[2]^2
  dy3 <- 3e7 * y[2]^2
  list(c(dy1, dy2, dy3))
}
print(radau(c(1, 0, 0), seq(0, 40, 10), f, NULL))
