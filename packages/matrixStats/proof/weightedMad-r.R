# Timing case for matrixStats::weightedMad: 20000 standard normal x,
# uniform weights, seed 1. One untimed call, then the median of 20.
# Also records the unweighted value, which must match stats::mad.
args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- sub("^--file=", "", file_arg[[1]])
data_path <- file.path(dirname(normalizePath(script)), "weightedMad-data.bin")

set.seed(1)
x <- rnorm(20000)
w <- runif(20000)
con <- file(data_path, "wb")
writeBin(c(x, w), con)
close(con)

one <- function() {
  matrixStats::weightedMad(x, w, na.rm = FALSE)
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
unweighted <- matrixStats::weightedMad(x)
if (!isTRUE(all.equal(unweighted, stats::mad(x), tolerance = 1e-8))) {
  stop("unweighted weightedMad does not match stats::mad")
}
cat(sprintf("%.17g\n", one()))
cat(sprintf("%.17g\n", unweighted))
cat(sprintf("%.17g\n", stats::median(elapsed) * 1000))
