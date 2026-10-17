suppressPackageStartupMessages({library(quantreg); library(SparseM)})
d <- as.matrix(read.table("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt"))
X <- d[,1:3]
y <- d[,4]
a <- as.matrix.csr(X)
one <- function() {
  f <- rq.fit.sfn(a, y, tau=0.3)
  c(f$coef, f$resid, f$it, f$ierr)
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
