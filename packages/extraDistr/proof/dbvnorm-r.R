suppressPackageStartupMessages(library(extraDistr))
fmt <- function(x) {
  if (is.matrix(x)) x <- as.vector(t(x))
  paste(sprintf("%.17g", as.vector(x)), collapse = ",")
}
ans <- dbvnorm(c(-1, 0, 1.5), c(0.2, -0.3, 0.7), mean1 = c(0, 1), mean2 = 0, sd1 = 1, sd2 = c(1, 1.5), cor = c(0.2, -0.4))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  dbvnorm(c(-1, 0, 1.5), c(0.2, -0.3, 0.7), mean1 = c(0, 1), mean2 = 0, sd1 = 1, sd2 = c(1, 1.5), cor = c(0.2, -0.4))
  elapsed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
}
cat(fmt(ans), "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed)))
