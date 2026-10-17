suppressPackageStartupMessages(library(extraDistr))
fmt <- function(x) {
  if (is.matrix(x)) x <- as.vector(t(x))
  paste(sprintf("%.17g", as.vector(x)), collapse = ",")
}
set.seed(1)
ans <- rbvnorm(4, mean1 = c(0, 1), mean2 = c(0, -1), sd1 = c(1, 2), sd2 = 1, cor = c(0, 0.5))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  rbvnorm(4, mean1 = c(0, 1), mean2 = c(0, -1), sd1 = c(1, 2), sd2 = 1, cor = c(0, 0.5))
  elapsed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
}
cat(fmt(ans), "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed)))
