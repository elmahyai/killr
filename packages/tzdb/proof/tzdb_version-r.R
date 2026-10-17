suppressPackageStartupMessages(library(tzdb))
invisible(tzdb_version())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  result <- tzdb_version()
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
med <- median(elapsed)
cat(sprintf("r_ms %.17g\n", med * 1000))
cat(result, "\n", sep = "")
