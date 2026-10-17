.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0.6")
options(warn = -1)
one <- function() {
  i3 <- diag(1, 3)
  a <- matrix(c(2, -1, 0, -1, 2, -1, 0, -1, 2), nrow = 3, byrow = TRUE)
  b <- matrix(c(2, -1, 2, -1, 2, -1, 2, -1, 2), nrow = 3, byrow = TRUE)
  c_mat <- matrix(c(-2, 1, 0, 1, -2, 1, 0, 1, -2), nrow = 3, byrow = TRUE)
  d <- matrix(c(-2, 1, -2, 1, -2, 1, -2, 1, -2), nrow = 3, byrow = TRUE)
  e <- matrix(c(1, 2, 0, 2, 1, 2, 0, 2, 1), nrow = 3, byrow = TRUE)
  bad2 <- matrix(c(1, 2, 2, 1), nrow = 2, byrow = TRUE)
  tiny_ev <- matrix(c(1, 0, 0, 1e-9), nrow = 2, byrow = TRUE)
  above_tol <- matrix(c(1, 0, 0, 1e-7), nrow = 2, byrow = TRUE)
  c(
    is.positive.definite(i3),
    is.positive.definite(a),
    is.positive.definite(b),
    is.positive.definite(c_mat),
    is.positive.definite(d),
    is.positive.definite(e),
    is.positive.definite(bad2),
    is.positive.definite(tiny_ev),
    is.positive.definite(above_tol),
    is.positive.definite(matrix(2.5)),
    is.positive.definite(matrix(1L)),
    is.positive.definite(matrix(1:9, 3, 3) + t(matrix(1:9, 3, 3)), tol = 1e-6)
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
