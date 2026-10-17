suppressPackageStartupMessages(library(extraDistr))
fmt <- function(x) {
  if (is.matrix(x)) x <- as.vector(t(x))
  paste(sprintf("%.17g", as.vector(x)), collapse = ",")
}
set.seed(1)
ans <- rbvpois(4, a = c(1, 0.5), b = 1.2, c = c(0.3, 0.1))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  rbvpois(4, a = c(1, 0.5), b = 1.2, c = c(0.3, 0.1))
  elapsed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
}
cat(fmt(ans), "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed)))
