suppressPackageStartupMessages(library(extraDistr))
value <- qlomax(c(0.1, 0.3, 0.5, 0.8), 1.5, 2.5)
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  qlomax(c(0.1, 0.3, 0.5, 0.8), 1.5, 2.5)
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
