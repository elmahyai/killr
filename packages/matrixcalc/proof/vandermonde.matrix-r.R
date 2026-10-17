.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
one <- function() {
  v1 <- vandermonde.matrix(c(2, 3, 5), 4)
  v2 <- vandermonde.matrix(c(1.5, -2), 3)
  v3 <- vandermonde.matrix(5, 4)
  v4 <- vandermonde.matrix(c(0.5, 1, 2, 4), 6)
  c(c(v1), c(v2), c(v3), c(v4))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
