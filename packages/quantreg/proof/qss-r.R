suppressPackageStartupMessages({library(quantreg); library(SparseM)})
x <- 2 * sin(1:12)
one <- function() {
  out <- c()
  for (dorder in c(1, 0)) {
    q <- qss(x, lambda = 2, Dorder = dorder)
    out <- c(out, q$x$x, as.vector(t(as.matrix(q$F))), as.vector(t(as.matrix(q$A))), q$lambda)
  }
  out
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
