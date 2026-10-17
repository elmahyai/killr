.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(BB))
fn <- function(x) sum((x - c(1, 2, 3))^2)
gr <- function(x) 2 * (x - c(1, 2, 3))
one <- function() {
  res <- BBoptim(c(0, 0, 0), fn, gr, control=list(checkGrad=FALSE, trace=FALSE), quiet=TRUE)
  c(res$par, res$value, res$gradient, res$fn.reduction, res$iter, res$feval, res$convergence, res$cpar)
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
