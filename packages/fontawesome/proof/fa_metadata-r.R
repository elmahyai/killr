suppressPackageStartupMessages(library(fontawesome))
invisible(fa_metadata())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  result <- fa_metadata()
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
cat(jsonlite::toJSON(result, auto_unbox = TRUE, digits = NA), "\n")
