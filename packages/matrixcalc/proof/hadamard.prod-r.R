.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
one <- function() {
  ex_x <- matrix(c(1, 2, 3, 4), nrow = 2, byrow = TRUE)
  ex_y <- matrix(c(2, 4, 6, 8), nrow = 2, byrow = TRUE)
  x <- matrix(seq(1, 4))
  y <- matrix(seq(5, 8))
  a <- matrix(seq(1, 6), nrow = 2, byrow = TRUE)
  b <- matrix(seq(11, 16), nrow = 2, byrow = TRUE)
  u <- c(0.25, -1.5, 2)
  v <- c(4, 0.5, -0.125)
  c(
    c(hadamard.prod(ex_x, ex_y)),
    c(hadamard.prod(x, y)),
    c(hadamard.prod(a, b)),
    c(hadamard.prod(u, v)),
    c(hadamard.prod(matrix(1:2, nrow = 1), matrix(3:4, nrow = 1)))
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
