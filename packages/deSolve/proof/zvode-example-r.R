.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))

spin <- function(t, y, parms) {
  list(1i * parms$w * y)
}

out <- zvode(c(z = 1 + 0i), seq(0, 6, by = 2), spin, list(w = 1.0))
print(out)
