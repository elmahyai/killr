# Timing case for matrixStats::iqrDiff: 100000 standard normals, set.seed(1).
# One untimed call, then the median of 20. Writes the sample for the Python script.
data_path <- "/tmp/matrixstats-iqrDiff.bin"
set.seed(1)
x <- rnorm(100000)
con <- file(data_path, "wb")
writeBin(x, con)
close(con)
one <- function() matrixStats::iqrDiff(x)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", one()))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
