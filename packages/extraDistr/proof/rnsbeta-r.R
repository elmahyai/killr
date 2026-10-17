suppressPackageStartupMessages(library(extraDistr))
one <- function() {
  rnsbeta(4, 5, 13, -4, 8)
}
set.seed(1)
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  set.seed(1)
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
