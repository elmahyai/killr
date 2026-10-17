suppressPackageStartupMessages(library(base64enc))
enc <- base64encode(1:100, 70)
invisible(base64decode(enc))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  result <- base64decode(enc)
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
med <- median(elapsed)
cat(sprintf("r_ms %.17g\n", med * 1000))
cat(paste(as.integer(result), collapse = " "), "\n")
