set.seed(1)
x <- rnorm(100000)
writeBin(x, "/tmp/matrixstats-seed1.bin")
one <- function() matrixStats::mean2(x, na.rm = FALSE, refine = TRUE)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
median(elapsed) * 1000
