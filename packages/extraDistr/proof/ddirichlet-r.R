suppressPackageStartupMessages(library(extraDistr))
fmt <- function(x) {
  if (is.matrix(x)) x <- as.vector(t(x))
  paste(sprintf("%.17g", as.vector(x)), collapse = ",")
}
x <- matrix(c(0.2, 0.3, 0.5, 0.1, 0.2, 0.7), ncol = 3, byrow = TRUE)
alpha <- matrix(c(1, 2, 3, 0.5, 0.5, 0.5), ncol = 3, byrow = TRUE)
ans <- ddirichlet(x, alpha)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  ddirichlet(x, alpha)
  elapsed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
}
cat(fmt(ans), "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed)))
