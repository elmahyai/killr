.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))

one <- function() {
  pairs <- matrix(c(2, 4, 2, 3, 5, 4), nrow = 2, byrow = TRUE)
  attr(pairs, "initialPartition") <- 1:5
  as.numeric(hclass(pairs, G = c(5, 3, 2)))
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
