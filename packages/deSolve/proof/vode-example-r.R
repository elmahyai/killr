.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
logist <- function(t, x, parms) {
  with(as.list(parms), {
    dx <- r * x[1] * (1 - x[1] / K)
    list(dx)
  })
}
print(vode(c(N = 0.1), seq(0, 10, 2), logist, c(r = 0.5, K = 100)))
