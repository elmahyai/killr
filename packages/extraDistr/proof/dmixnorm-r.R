suppressPackageStartupMessages(library(extraDistr))
fmt <- function(x) {
  if (is.matrix(x)) x <- as.vector(t(x))
  paste(sprintf("%.17g", as.vector(x)), collapse = ",")
}
ans <- dmixnorm(c(-1, 0, 2, 5), c(0, 3), c(1, 1.5), c(0.4, 0.6))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  dmixnorm(c(-1, 0, 2, 5), c(0, 3), c(1, 1.5), c(0.4, 0.6))
  elapsed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
}
cat(fmt(ans), "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed)))
