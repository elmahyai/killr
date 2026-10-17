.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
one <- function() {
  a <- matrix(seq(1, 12, 1), nrow = 3, byrow = TRUE)
  b <- matrix(seq(1, 16, 1), nrow = 4, byrow = TRUE)
  c(
    is.square.matrix(a),
    is.square.matrix(b),
    is.square.matrix(matrix(3.5)),
    is.square.matrix(matrix(numeric(0), 0, 0)),
    is.square.matrix(matrix(0, 2, 3)),
    is.square.matrix(matrix(1:4, 2, 2)),
    is.square.matrix(matrix(c(TRUE, FALSE, TRUE, TRUE), 2, 2)),
    is.square.matrix(matrix(0, 64, 64))
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
