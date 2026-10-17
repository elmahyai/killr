set.seed(1)
X <- matrix(rnorm(500 * 200), nrow = 500, ncol = 200)
S <- cbind(1:30, 31:60, 61:90, 91:120)
writeBin(as.numeric(X), "/tmp/rowavgs-seed1.bin")
one <- function() matrixStats::rowAvgsPerColSet(X, S = S)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
median(elapsed) * 1000
