suppressPackageStartupMessages(library(fontawesome))
invisible(fa("r-project", fill = "red", title = "R"))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  result <- as.character(fa("r-project", fill = "red", title = "R"))
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
cat(result, "\n")
