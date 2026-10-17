suppressPackageStartupMessages(library(jquerylib))

result <- jquery_core()
invisible(result)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  result <- jquery_core()
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
cat(jsonlite::toJSON(unclass(result), auto_unbox = TRUE, null = "null"), "\n")
