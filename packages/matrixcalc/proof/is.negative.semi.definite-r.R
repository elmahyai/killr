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
  tiny_ev <- matrix(c(-1, 0, 0, -1e-9), nrow = 2, byrow = TRUE)
  above_tol <- matrix(c(-1, 0, 0, -1e-7), nrow = 2, byrow = TRUE)
  base <- matrix(1:9, 3, 3)
  custom_tol <- base + t(base)
  c(
    is.negative.semi.definite(i3),
    is.negative.semi.definite(a),
    is.negative.semi.definite(b),
    is.negative.semi.definite(c_mat),
    is.negative.semi.definite(d),
    is.negative.semi.definite(e),
    is.negative.semi.definite(bad2),
    is.negative.semi.definite(tiny_ev),
    is.negative.semi.definite(above_tol),
    is.negative.semi.definite(matrix(-2.5)),
    is.negative.semi.definite(matrix(1L)),
    is.negative.semi.definite(-custom_tol, tol = 1e-6)
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
