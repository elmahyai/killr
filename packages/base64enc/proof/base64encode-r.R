suppressPackageStartupMessages(library(base64enc))
x <- 1:100
invisible(base64encode(x, 70))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  result <- base64encode(x, 70)
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
med <- median(elapsed)
cat(sprintf("r_ms %.17g\n", med * 1000))
cat(result, sep = "\n")
cat("\n")
