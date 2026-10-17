.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
one <- function() {
  x <- matrix(seq(1, 16, 1), nrow = 4, byrow = TRUE)
  y <- matrix(seq(1, 4, 1), nrow = 2, byrow = TRUE)
  a <- matrix(seq(1, 24, 1), nrow = 6, byrow = TRUE)
  b <- matrix(c(0.1, -1.5, 2.25, 4, 0.5, -0.25), nrow = 2, byrow = TRUE)
  cmat <- matrix(seq(1, 25, 1), nrow = 5, byrow = TRUE)
  d <- matrix(7.125, nrow = 1, ncol = 1)
  e <- matrix(seq(1, 18, 1), nrow = 3, byrow = TRUE)
  f <- matrix(c(9, 8, 7, 6), nrow = 2, byrow = TRUE)
  parts <- list(
    c(set.submatrix(x, y, 3, 3)),
    c(set.submatrix(a, b, 1, 1)),
    c(set.submatrix(cmat, d, 5, 5)),
    c(set.submatrix(e, f, 2, 4))
  )
  unlist(parts)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
