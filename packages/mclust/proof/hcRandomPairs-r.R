.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))

one <- function() {
  as.numeric(hcRandomPairs(matrix(1:2, nrow = 2, ncol = 1), seed = 7))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
