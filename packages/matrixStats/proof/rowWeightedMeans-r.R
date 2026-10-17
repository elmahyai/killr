# Timing case for matrixStats::rowWeightedMeans: 400 by 250 standard normals,
# uniform weights, seed 1. One untimed call, then the median of 20.
args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- sub("^--file=", "", file_arg[[1]])
root <- dirname(normalizePath(script))
data_path <- file.path(root, "rowWeightedMeans-data.bin")
result_path <- file.path(root, "rowWeightedMeans-result.bin")

set.seed(1)
x <- matrix(rnorm(400 * 250), nrow = 400, ncol = 250)
w <- runif(ncol(x))
con <- file(data_path, "wb")
writeBin(c(as.numeric(x), as.numeric(w)), con)
close(con)

one <- function() {
  matrixStats::rowWeightedMeans(x, w = w, na.rm = FALSE)
}
first <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
out <- file(result_path, "wb")
writeBin(as.numeric(first), out)
close(out)
cat(sprintf("%.17g\n", median(elapsed) * 1000))
