suppressPackageStartupMessages(library(extraDistr))
fmt <- function(x) {
  if (is.matrix(x)) x <- as.vector(t(x))
  paste(sprintf("%.17g", as.numeric(x)), collapse = ",")
}
set.seed(1)
value <- rcatlp(4, log(c(0.1, 0.2, 0.7)))
cat(fmt(value), "\n", sep = "")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  rcatlp(4, log(c(0.1, 0.2, 0.7)))
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
