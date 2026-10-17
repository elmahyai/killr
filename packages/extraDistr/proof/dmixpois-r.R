suppressPackageStartupMessages(library(extraDistr))
fmt <- function(x) {
  if (is.matrix(x)) x <- as.vector(t(x))
  paste(sprintf("%.17g", as.vector(x)), collapse = ",")
}
ans <- dmixpois(c(0, 1, 3, 8), c(1, 5), c(0.3, 0.7))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  dmixpois(c(0, 1, 3, 8), c(1, 5), c(0.3, 0.7))
  elapsed[[i]] <- (as.numeric(Sys.time()) - t0) * 1000
}
cat(fmt(ans), "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed)))
