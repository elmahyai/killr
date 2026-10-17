dir.create("/tmp/ms-rowquantiles-check", showWarnings = FALSE, recursive = TRUE)
set.seed(1)
x <- matrix(rnorm(200 * 80), nrow = 200, ncol = 80)
x[1, 1] <- NA
one <- function() {
  list(
    matrixStats::iqr(x, na.rm = FALSE),
    matrixStats::iqr(x, na.rm = TRUE)
  )
}
ans <- one()
writeBin(as.numeric(ans[[1]]), "/tmp/ms-rowquantiles-check/iqr-false.bin")
writeBin(as.numeric(ans[[2]]), "/tmp/ms-rowquantiles-check/iqr-true.bin")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- (as.numeric(Sys.time()) - t0) * 1000
}
cat(median(elapsed), "\n")
