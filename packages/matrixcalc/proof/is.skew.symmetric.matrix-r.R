.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0-6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
one <- function() {
  a <- diag(1, 3)
  b <- matrix(c(0, -2, -1, -2, 0, -4, 1, 4, 0), nrow = 3, byrow = TRUE)
  c <- matrix(c(0, 2, 1, 2, 0, 4, 1, 4, 0), nrow = 3, byrow = TRUE)
  d <- matrix(c(1, 2, 3, 4), nrow = 2, byrow = TRUE)
  near <- matrix(c(0, -1 + 1e-9, 1, 0), nrow = 2, byrow = TRUE)
  far <- matrix(c(0, -1 + 1e-7, 1, 0), nrow = 2, byrow = TRUE)
  empty <- matrix(numeric(0), 0, 0)
  na_case <- matrix(c(0, NA, 0, 0), nrow = 2, byrow = TRUE)
  nan_case <- matrix(c(0, NaN, 0, 0), nrow = 2, byrow = TRUE)
  inf_case <- matrix(c(0, Inf, -Inf, 0), nrow = 2, byrow = TRUE)
  c(
    is.skew.symmetric.matrix(a),
    is.skew.symmetric.matrix(b),
    is.skew.symmetric.matrix(c),
    is.skew.symmetric.matrix(d),
    is.skew.symmetric.matrix(near),
    is.skew.symmetric.matrix(far),
    is.skew.symmetric.matrix(empty),
    is.skew.symmetric.matrix(matrix(3.5)),
    is.skew.symmetric.matrix(na_case),
    is.skew.symmetric.matrix(nan_case),
    is.skew.symmetric.matrix(inf_case),
    is.skew.symmetric.matrix(matrix(0, 64, 64)),
    is.skew.symmetric.matrix(matrix(c(0L, -1L, 1L, 0L), 2, 2))
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
