.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(rootSolve))
model <- function(t, y, parms) list(c(-0.1*y[1] + 0.02*y[2], 0.1*y[1] - 0.2*y[2]))
y <- c(A = 1, B = 2)
one <- function() as.vector(jacobian.full(y, model))
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
