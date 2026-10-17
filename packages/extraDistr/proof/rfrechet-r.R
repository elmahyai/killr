suppressPackageStartupMessages(library(extraDistr))
set.seed(1)
value <- rfrechet(4, 1.5, 0, 1)
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  rfrechet(4, 1.5, 0, 1)
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
