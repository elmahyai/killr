# Time matrixStats::allocVector. One untimed call, then the median of 20.
# Sys.time() differences are reported in milliseconds.
# The timed call is allocVector(1000000, 1.5).
library(matrixStats)

one <- function() allocVector(1000000, 1.5)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
y <- one()
writeBin(as.numeric(y), "/tmp/ms-allocVector-r.bin")
meta <- file("/tmp/ms-allocVector-r.meta", "w")
writeLines(c(
  storage.mode(y),
  sprintf("%d", length(y)),
  sprintf("%.17g", y[[1]]),
  sprintf("%d", sum(y != 1.5))
), meta)
close(meta)
cat(sprintf("%.17g\n", median(elapsed) * 1000))
