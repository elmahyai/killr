suppressPackageStartupMessages({library(quantreg); library(SparseM)})
d <- as.matrix(read.table("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt"))
X <- d[,1:3]
y <- d[,4]
a <- as.matrix.csr(X)
R1 <- as.matrix.csr(matrix(c(0,0,1), 1, 3))
R2 <- as.matrix.csr(rbind(c(0,0,1), c(0,1,0)))
one <- function() {
  f1 <- rq.fit.sfnc(a, y, R1, 0, tau=0.5)
  f2 <- rq.fit.sfnc(a, y, R2, c(0, 3), tau=0.25)
  c(f1$coef, f1$resid, f1$it, f1$ierr, f2$coef, f2$resid, f2$it, f2$ierr)
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
