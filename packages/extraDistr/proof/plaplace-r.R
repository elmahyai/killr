suppressPackageStartupMessages(library(extraDistr))
value <- plaplace(c(-2, -0.5, 0.5, 3), 0.5, 1.5)
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  plaplace(c(-2, -0.5, 0.5, 3), 0.5, 1.5)
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
