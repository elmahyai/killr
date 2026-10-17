.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(slam))

one <- function() {
  a <- as.simple_sparse_array(matrix(c(1, 0, 0, 0), 2, 2))
  b <- as.simple_sparse_array(matrix(c(0, 0, 2, 0), 2, 2))
  as.numeric(as.array(abind_simple_sparse_array(a, b, MARGIN=1)))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
