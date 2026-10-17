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
  mixed2 <- matrix(c(1, 0, 0, -1), nrow = 2, byrow = TRUE)
  tiny_pos <- matrix(c(1e-9, 0, 0, -1), nrow = 2, byrow = TRUE)
  above_tol <- matrix(c(1e-7, 0, 0, -1), nrow = 2, byrow = TRUE)
  c(
    is.indefinite(i3),
    is.indefinite(a),
    is.indefinite(b),
    is.indefinite(c_mat),
    is.indefinite(d),
    is.indefinite(e),
    is.indefinite(bad2),
    is.indefinite(mixed2),
    is.indefinite(tiny_pos),
    is.indefinite(above_tol),
    is.indefinite(matrix(2.5)),
    is.indefinite(matrix(1L))
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
