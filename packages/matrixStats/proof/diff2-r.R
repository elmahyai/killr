# Time matrixStats::diff2. One untimed call, then the median of 20.
# Sys.time() differences are reported in milliseconds.
# The sample is 100000 standard normal values with seed 1.
args <- commandArgs(trailingOnly = TRUE)
dest <- if (length(args) >= 1) args[[1]] else "."
set.seed(1)
x <- rnorm(100000)
one <- function() matrixStats::diff2(x, lag = 1, differences = 1)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
y <- one()
cat(sprintf("%.17g\n", median(elapsed) * 1000))
writeLines(sprintf("%.17g", x), file.path(dest, "diff2-x.txt"))
writeLines(sprintf("%.17g", y), file.path(dest, "diff2-y.txt"))
