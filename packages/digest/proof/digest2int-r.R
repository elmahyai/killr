suppressPackageStartupMessages(library(digest))
x <- "The quick brown fox jumps over the lazy dog"
invisible(digest2int(x, 0L))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  result <- digest2int(x, 0L)
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
med <- median(elapsed)
cat(sprintf("r_ms %.17g\n", med * 1000))
cat(sprintf("result %d\n", result))
