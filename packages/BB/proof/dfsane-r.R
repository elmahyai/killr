.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(BB))
sys <- function(x) c(x[1] - 1, x[2] - 2)
one <- function() {
  res <- dfsane(c(0, 0), sys, control=list(NM=FALSE, BFGS=FALSE, trace=FALSE), quiet=TRUE)
  c(res$par, res$residual, res$fn.reduction, res$feval, res$iter, res$convergence)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse=","), "
", sep="")
cat("MS
")
cat(sprintf("%.17g
", median(elapsed) * 1000))
