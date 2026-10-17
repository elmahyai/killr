options(matrixStats.ties.method.missing = "ignore")
set.seed(1)
x <- matrix(rnorm(200 * 80), nrow = 200, ncol = 80)
writeBin(as.numeric(x), "rowRanks-x.bin")
one <- function() matrixStats::rowRanks(x)
y <- one()
writeBin(as.integer(y), "rowRanks-y.bin")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
median(elapsed) * 1000
