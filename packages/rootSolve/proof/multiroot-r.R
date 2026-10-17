.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(rootSolve))
model <- function(x) c(x[1]^2 + x[2]^2 - 1, x[1]^2 - x[2]^2 + 0.5)
one <- function() {
multiroot(model, c(1, 1))$root
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
