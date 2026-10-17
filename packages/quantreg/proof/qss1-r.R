suppressPackageStartupMessages({library(quantreg); library(SparseM)})
x <- 2 * sin(1:12)
one <- function() {
  q <- qss1(x, lambda = 2)
  c(q$x$x, as.vector(t(as.matrix(q$F))), as.vector(t(as.matrix(q$A))), q$lambda)
}
invisible(one())
elapsed <- numeric(20)
for (k in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[k]] <- as.numeric(Sys.time()) - t0
}
value <- one()
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
