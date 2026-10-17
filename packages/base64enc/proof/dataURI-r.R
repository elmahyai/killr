suppressPackageStartupMessages(library(base64enc))
x <- as.raw(1:10)
invisible(dataURI(x))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  result <- dataURI(x)
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
med <- median(elapsed)
cat(sprintf("r_ms %.17g\n", med * 1000))
cat(result, "\n")
