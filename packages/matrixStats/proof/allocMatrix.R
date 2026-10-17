# Time matrixStats::allocMatrix. One untimed call, then the median of 20.
# Sys.time() differences are reported in milliseconds.
# The timed call is allocMatrix(2000, 500, 1.5).
library(matrixStats)

one <- function() allocMatrix(2000L, 500L, 1.5)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
y <- one()
writeBin(as.numeric(y), "/tmp/ms-allocMatrix-r.bin")
meta <- file("/tmp/ms-allocMatrix-r.meta", "w")
writeLines(c(
  storage.mode(y),
  paste(dim(y), collapse = " "),
  sprintf("%.17g", y[[1]]),
  sprintf("%d", sum(y != 1.5))
), meta)
close(meta)
cat(sprintf("%.17g\n", median(elapsed) * 1000))
