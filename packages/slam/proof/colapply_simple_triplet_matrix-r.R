.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(slam))

one <- function() {
  m <- simple_triplet_matrix(i=c(1,2,1), j=c(1,1,2), v=c(1,2,3), nrow=2, ncol=2)
  as.numeric(colapply_simple_triplet_matrix(m, sum))
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
