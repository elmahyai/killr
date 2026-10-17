suppressPackageStartupMessages(library(tzdb))
invisible(tzdb_initialize())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  result <- tzdb_initialize()
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
med <- median(elapsed)
cat(sprintf("r_ms %.17g\n", med * 1000))
cat(if (is.null(result)) "NULL\n" else "NOTNULL\n")
