.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
one <- function() {
  a <- diag(1, 3)
  b <- matrix(c(1, 2, 3, 4), nrow = 2, byrow = TRUE)
  c <- matrix(c(1, 0, 0, 0), nrow = 2, byrow = TRUE)
  near <- matrix(c(1, 0, 0, 1e-9), nrow = 2, byrow = TRUE)
  far <- matrix(c(1, 0, 0, 1e-7), nrow = 2, byrow = TRUE)
  empty <- matrix(numeric(0), 0, 0)
  na_case <- matrix(c(1, NA, 0, 2), nrow = 2, byrow = TRUE)
  nan_case <- matrix(c(1, NaN, NaN, 2), nrow = 2, byrow = TRUE)
  inf_case <- matrix(c(1, Inf, 0, 2), nrow = 2, byrow = TRUE)
  c(
    is.idempotent.matrix(a),
    is.idempotent.matrix(b),
    is.idempotent.matrix(c),
    is.idempotent.matrix(near),
    is.idempotent.matrix(far),
    is.idempotent.matrix(empty),
    is.idempotent.matrix(matrix(3.5)),
    is.idempotent.matrix(na_case),
    is.idempotent.matrix(nan_case),
    is.idempotent.matrix(inf_case),
    is.idempotent.matrix(matrix(1L:4L, 2, 2))
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
