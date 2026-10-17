suppressPackageStartupMessages(library(fontawesome))
invisible(fa_i("r-project"))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  result <- as.character(fa_i("r-project"))
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
cat(result, "\n")
