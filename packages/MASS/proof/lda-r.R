.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
one <- function() {
  set.seed(42)
  x <- matrix(rnorm(60), 30, 2)
  g <- factor(rep(c("A", "B", "C"), each = 10))
  z <- lda(x, g)
  c(
    as.vector(z$prior),
    as.vector(z$counts),
    as.vector(z$means),
    as.vector(z$scaling),
    z$svd,
    z$N
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
if (is.character(value)) cat(value, "\n", sep = "\n") else cat(sprintf("%.17g\n", as.numeric(value)))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
