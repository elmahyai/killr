set.seed(1)
lx <- log(abs(rnorm(100000)) + 1e-12)
writeBin(lx, "proof/logSumExp-lx.bin")
one <- function() matrixStats::logSumExp(lx, na.rm = FALSE)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", one()))
cat(median(elapsed) * 1000, "\n")
