suppressPackageStartupMessages({library(quantreg); library(SparseM)})
d <- as.matrix(read.table("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt"))
xs <- c(0.1, 0.5, 0.9, 0.3, 0.7, 0.2)
ys <- c(0.2, 0.4, 0.1, 0.8, 0.6, 0.3)
xd <- d[, 2]
yd <- d[, 3]
mat <- function(M) { A <- as.matrix(M); c(dim(A), as.vector(t(A))) }
one <- function() {
  a <- triogram.penalty(xs, ys)
  b <- triogram.penalty(xd, yd)
  c(mat(a), mat(b))
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
value <- one()
cat(paste(sprintf("%.17g", as.numeric(value)), collapse=","), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
