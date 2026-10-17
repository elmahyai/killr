suppressPackageStartupMessages(library(quantreg))
suppressPackageStartupMessages(library(SparseM))
d <- as.matrix(read.table("/home/ahmed/killr_projects/killr/packages/quantreg/quantreg/data/check_design.txt"))
X <- d[,1:3]; y <- d[,4]
# Sparse design: the slope entries with |x| < 0.5 are structural zeros; the intercept stays.
X[, 2:3][abs(X[, 2:3]) < 0.5] <- 0
one <- function() {
  set.seed(1)
  a <- as.matrix.csr(X)
  U <- matrix(runif(length(y) * 200), length(y), 200)
  W <- as.matrix(t(a) %*% ((U < 0.5) - 0.5))
  as.numeric(quantreg:::boot.rq.spwy(W, a, y, tau=0.5))
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time()); one(); elapsed[[i]] <- as.numeric(Sys.time())-t0
}
value <- one()
cat(paste(sprintf("%.17g", as.numeric(value)), collapse=","), "\n")
cat(sprintf("%.17g\n", median(elapsed)*1000))
