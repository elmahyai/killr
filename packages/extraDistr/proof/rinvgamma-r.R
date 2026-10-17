suppressPackageStartupMessages(library(extraDistr))
one <- function() {
  rinvgamma(4, 20, 3)
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
