suppressPackageStartupMessages(library(extraDistr))
fmt <- function(x) {
  if (is.matrix(x)) x <- as.vector(t(x))
  paste(sprintf("%.17g", as.numeric(x)), collapse = ",")
}
value <- dmnom(c(1, 2, 3), 6, c(0.2, 0.3, 0.5))
cat(fmt(value), "\n", sep = "")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  dmnom(c(1, 2, 3), 6, c(0.2, 0.3, 0.5))
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
