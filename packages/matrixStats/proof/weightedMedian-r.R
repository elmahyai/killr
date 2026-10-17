# Timing case for matrixStats::weightedMedian: 100000 standard normal x,
# uniform weights, seed 1, na.rm FALSE, default interpolate and ties.
# One untimed call, then the median of 20. Writes the sample for the Python script.
args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- sub("^--file=", "", file_arg[[1]])
data_path <- file.path(dirname(normalizePath(script)), "weightedMedian-data.bin")

set.seed(1)
x <- rnorm(100000)
w <- runif(100000)
con <- file(data_path, "wb")
writeBin(c(x, w), con)
close(con)

one <- function() {
  matrixStats::weightedMedian(x, w, na.rm = FALSE)
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", one()))
cat(sprintf("%.17g\n", stats::median(elapsed) * 1000))
