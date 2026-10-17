lx <- matrix(readBin("/tmp/rowlogsumexps-seed1.bin", "double", 400 * 250), nrow = 400, ncol = 250)
one <- function() matrixStats::rowLogSumExps(lx, na.rm = FALSE)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
writeBin(as.numeric(one()), "/tmp/rowLogSumExps-r.bin")
