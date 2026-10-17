suppressPackageStartupMessages(library(extraDistr))
fmt <- function(x) {
  if (is.matrix(x)) x <- as.vector(t(x))
  paste(sprintf("%.17g", as.numeric(x)), collapse = ",")
}
value <- ddweibull(0:5, 0.4, 1.3)
cat(fmt(value), "\n", sep = "")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  ddweibull(0:5, 0.4, 1.3)
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
