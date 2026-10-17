# Timing case for matrixStats::weightedSd: 100000 standard normal x,
# uniform weights, seed 1. One untimed call, then the median of 20.
args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- sub("^--file=", "", file_arg[[1]])
data_path <- file.path(dirname(normalizePath(script)), "weightedSd-data.bin")

set.seed(1)
x <- rnorm(100000)
w <- runif(100000)
con <- file(data_path, "wb")
writeBin(c(x, w), con)
close(con)

one <- function() matrixStats::weightedSd(x, w)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
value <- one()
writeBin(value, "/tmp/weightedSd-r-value.bin")
cat(sprintf("%.17g\n", value))
cat(sprintf("%.17g\n", stats::median(elapsed) * 1000))
