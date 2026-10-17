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
  base <- matrix(1:9, 3, 3)
  custom_tol <- base + t(base)
  c(
    is.positive.semi.definite(i3),
    is.positive.semi.definite(a),
    is.positive.semi.definite(b),
    is.positive.semi.definite(c_mat),
    is.positive.semi.definite(d),
    is.positive.semi.definite(e),
    is.positive.semi.definite(bad2),
    is.positive.semi.definite(tiny_ev),
    is.positive.semi.definite(above_tol),
    is.positive.semi.definite(matrix(2.5)),
    is.positive.semi.definite(matrix(1L)),
    is.positive.semi.definite(custom_tol, tol = 1e-6)
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
