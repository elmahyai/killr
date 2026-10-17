set.seed(1)
x <- rnorm(100000)
writeBin(x, "/tmp/matrixstats-seed1.bin")
one <- function() matrixStats::sum2(x, na.rm = FALSE)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
median(elapsed) * 1000
