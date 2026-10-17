.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))
one <- function() {
  train <- matrix(
    c(
      1.2, 0.5,
      1.5, 0.7,
      1.1, 0.9,
      1.8, 0.4,
      1.3, 0.6,
      3.1, 2.2,
      3.4, 2.5,
      2.9, 2.1,
      3.6, 2.8,
      3.2, 2.4,
      5.5, 4.1,
      5.8, 4.3,
      5.2, 3.9,
      6.1, 4.5,
      5.6, 4.0
    ),
    15, 2, byrow = TRUE
  )
  cl <- factor(c(rep("A", 5), rep("B", 5), rep("C", 5)))
  z <- qda(train, cl)
  c(
    as.vector(z$prior),
    as.vector(z$means),
    as.vector(z$scaling),
    z$ldet
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", as.numeric(value)))
cat(sprintf("%.17g\n", median(elapsed) * 1000))
