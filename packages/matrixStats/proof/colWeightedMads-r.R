# Timing case for matrixStats::colWeightedMads: a 40 by 200 matrix of
# standard normals, uniform row weights, seed 1.
# One untimed call, then the median of 20.
args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- sub("^--file=", "", file_arg[[1]])
data_path <- file.path(dirname(normalizePath(script)), "colWeightedMads-data.bin")

set.seed(1)
x <- matrix(rnorm(40 * 200), nrow = 40, ncol = 200)
w <- runif(40)
con <- file(data_path, "wb")
writeBin(c(as.numeric(x), w), con)
close(con)

one <- function() {
  matrixStats::colWeightedMads(x, w, na.rm = FALSE)
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", one()), collapse = "\n"), "\n", sep = "")
cat(sprintf("%.17g\n", stats::median(elapsed) * 1000))
