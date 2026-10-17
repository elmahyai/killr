suppressPackageStartupMessages(library(extraDistr))
fmt <- function(x) {
  if (is.matrix(x)) x <- as.vector(t(x))
  paste(sprintf("%.17g", as.vector(x)), collapse = ",")
}
ans <- dbvpois(c(0, 1, 2, 3), c(1, 1, 0, 2), a = c(1, 1.5), b = 0.8, c = c(0.2, 0.5))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  dbvpois(c(0, 1, 2, 3), c(1, 1, 0, 2), a = c(1, 1.5), b = 0.8, c = c(0.2, 0.5))
  elapsed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
}
cat(fmt(ans), "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed)))
