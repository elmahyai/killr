.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(quadprog))
Dmat <- diag(3)
dvec <- c(0, 5, 0)
Amat <- rbind(c(-4, 2, -2), c(-3, 1, 1))
Aind <- rbind(c(2, 2, 2), c(1, 1, 2), c(2, 2, 3))
bvec <- c(-8, 2, 0)
one <- function() {
  res <- solve.QP.compact(Dmat, dvec, Amat, Aind, bvec=bvec)
  c(res$solution, res$value, res$unconstrained.solution, res$iterations, res$Lagrangian, res$iact)
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
