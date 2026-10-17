suppressPackageStartupMessages(library(extraDistr))
value <- dgev(c(-1, 0, 1, 2), 0, 1, -0.2)
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  dgev(c(-1, 0, 1, 2), 0, 1, -0.2)
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
