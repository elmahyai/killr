suppressPackageStartupMessages(library(extraDistr))
fmt <- function(x) {
  if (is.matrix(x)) x <- as.vector(t(x))
  paste(sprintf("%.17g", as.numeric(x)), collapse = ",")
}
value <- qzinb(c(0.1, 0.4, 0.8), 2, 0.4, 0.25)
cat(fmt(value), "\n", sep = "")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  qzinb(c(0.1, 0.4, 0.8), 2, 0.4, 0.25)
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
