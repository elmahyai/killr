suppressPackageStartupMessages(library(extraDistr))
fmt <- function(x) {
  if (is.matrix(x)) x <- as.vector(t(x))
  paste(sprintf("%.17g", as.vector(x)), collapse = ",")
}
set.seed(1)
alpha <- matrix(c(1, 1, 1, 2, 3, 4), ncol = 3, byrow = TRUE)
ans <- rdirichlet(4, alpha)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  rdirichlet(4, alpha)
  elapsed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
}
cat(fmt(ans), "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed)))
