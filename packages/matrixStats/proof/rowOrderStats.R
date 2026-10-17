set.seed(1)
x <- matrix(rnorm(400 * 250), nrow = 400, ncol = 250)
writeBin(as.numeric(x), "rowOrderStats-x.bin")
one <- function() matrixStats::rowOrderStats(x, which = 1)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
median(elapsed) * 1000
