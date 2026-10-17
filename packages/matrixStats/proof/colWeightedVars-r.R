# Timing case for matrixStats::colWeightedVars: 400 by 250 standard normal
# matrix, seed 1. One untimed call, then the median of 20.
args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- sub("^--file=", "", file_arg[[1]])
data_path <- file.path(dirname(normalizePath(script)), "colWeightedVars-data.bin")

set.seed(1)
x <- matrix(rnorm(400 * 250), nrow = 400, ncol = 250)
con <- file(data_path, "wb")
writeBin(as.numeric(x), con)
close(con)

one <- function() matrixStats::colWeightedVars(x)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
value <- one()
writeBin(as.numeric(value), "/tmp/colWeightedVars-r-value.bin")
cat(sprintf("%.17g\n", stats::median(elapsed) * 1000))
