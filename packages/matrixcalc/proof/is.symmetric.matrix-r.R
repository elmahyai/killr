.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0.6")
options(warn = -1)
one <- function() {
  a <- matrix(c(1, 2, 3, 4), nrow = 2, byrow = TRUE)
  b <- matrix(c(1, 2, 2, 1), nrow = 2, byrow = TRUE)
  empty <- matrix(numeric(0), 0, 0)
  tiny <- matrix(c(1, 1 + 1e-9, 0, 2), nrow = 2, byrow = TRUE)
  na_case <- matrix(c(1, NA, 0, 1), nrow = 2, byrow = TRUE)
  nan_case <- matrix(c(1, NaN, NaN, 2), nrow = 2, byrow = TRUE)
  inf_case <- matrix(c(1, Inf, 0, 2), nrow = 2, byrow = TRUE)
  c(
    is.symmetric.matrix(a),
    is.symmetric.matrix(b),
    is.symmetric.matrix(empty),
    is.symmetric.matrix(matrix(3.5)),
    is.symmetric.matrix(tiny),
    is.symmetric.matrix(na_case),
    is.symmetric.matrix(nan_case),
    is.symmetric.matrix(inf_case),
    is.symmetric.matrix(matrix(0, 64, 64)),
    is.symmetric.matrix(matrix(1L:4L, 2, 2))
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
