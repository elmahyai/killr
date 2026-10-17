x <- matrix(readBin("/tmp/rowdiffs-seed1.bin", "double", 400 * 250), nrow = 400, ncol = 250)
one <- function() matrixStats::rowDiffs(x, lag = 1L, differences = 1L)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
median(elapsed) * 1000
