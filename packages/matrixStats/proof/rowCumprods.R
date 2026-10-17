x <- matrix(readBin("/tmp/rowcumprods-seed1.bin", "double", 200 * 80), nrow = 200, ncol = 80)
one <- function() matrixStats::rowCumprods(x)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
median(elapsed) * 1000
