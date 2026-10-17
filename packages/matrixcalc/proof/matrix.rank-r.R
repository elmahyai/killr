.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0.6")
options(warn = -1)
one <- function() {
  a <- diag(seq(1, 4, 1))
  b <- matrix(seq(1, 16, 1), nrow = 4, byrow = TRUE)
  singular <- matrix(c(1, 2, 2, 4), nrow = 2, byrow = TRUE)
  c(
    matrix.rank(a),
    matrix.rank(b),
    matrix.rank(a, method = "chol"),
    matrix.rank(b, method = "chol"),
    matrix.rank(singular),
    matrix.rank(singular, method = "chol"),
    matrix.rank(matrix(3.5)),
    matrix.rank(matrix(numeric(0), 0, 0)),
    matrix.rank(matrix(1:4, 2, 2)),
    matrix.rank(matrix(c(TRUE, FALSE, TRUE, TRUE), 2, 2))
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
