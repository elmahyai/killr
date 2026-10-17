.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(slam))

one <- function() {
  m <- simple_triplet_zero_matrix(2, 3)
  c(m$nrow, m$ncol, length(m$v))
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
