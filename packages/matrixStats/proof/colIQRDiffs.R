# Timing case for matrixStats::colIQRDiffs: 200 by 80 standard normals, set.seed(1).
# One untimed call, then the median of 20. The matrix is stored column-major.
data_path <- "/tmp/matrixstats-colIQRDiffs.bin"
set.seed(1)
x <- matrix(rnorm(200 * 80), nrow = 200, ncol = 80)
con <- file(data_path, "wb")
writeBin(as.numeric(x), con)
close(con)
one <- function() matrixStats::colIQRDiffs(x)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", one()), collapse = " "), "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
