.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
one <- function() {
  a <- diag(1, 3)
  b <- matrix(c(0, 0, 3, 4), nrow = 2, byrow = TRUE)
  full <- matrix(c(1, 2, 3, 4), nrow = 2, byrow = TRUE)
  singular <- matrix(c(1, 2, 2, 4), nrow = 2, byrow = TRUE)
  tiny_det <- matrix(c(1e-9, 0, 0, 1), nrow = 2, byrow = TRUE)
  above_tol <- matrix(c(1e-7, 0, 0, 1), nrow = 2, byrow = TRUE)
  empty <- matrix(numeric(0), 0, 0)
  na_case <- matrix(c(1, NA, 0, 2), nrow = 2, byrow = TRUE)
  c(
    is.non.singular.matrix(a),
    is.non.singular.matrix(b),
    is.non.singular.matrix(full),
    is.non.singular.matrix(singular),
    is.non.singular.matrix(tiny_det),
    is.non.singular.matrix(above_tol),
    is.non.singular.matrix(empty),
    is.non.singular.matrix(matrix(3.5)),
    is.non.singular.matrix(matrix(1L:4L, 2, 2)),
    is.non.singular.matrix(tiny_det, tol = 1e-10),
    is.non.singular.matrix(na_case)
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
