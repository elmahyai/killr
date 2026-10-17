# Timing case for matrixStats::t_tx_OP_y: 400 by 250 standard normal matrix,
# conforming y of length 250, seed 1, OP "+".
# One untimed call, then the median of 20. Writes the sample and the result.
args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- sub("^--file=", "", file_arg[[1]])
dir <- dirname(normalizePath(script))
data_path <- file.path(dir, "t_tx_OP_y-data.bin")
ans_path <- file.path(dir, "t_tx_OP_y-ans.bin")

set.seed(1)
x <- matrix(rnorm(400 * 250), nrow = 400, ncol = 250)
y <- rnorm(250)
con <- file(data_path, "wb")
writeBin(c(as.numeric(x), y), con)
close(con)

one <- function() {
  matrixStats::t_tx_OP_y(x, y, OP = "+")
}
ans <- one()
con <- file(ans_path, "wb")
writeBin(as.numeric(ans), con)
close(con)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", stats::median(elapsed) * 1000))
