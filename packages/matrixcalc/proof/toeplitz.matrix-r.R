.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
one <- function() {
  t4 <- toeplitz.matrix(4, seq(1, 7))
  t3 <- toeplitz.matrix(3, c(1, 2, 3, 4, 5))
  t2 <- toeplitz.matrix(2, c(10, 20, 30))
  c(c(t4), c(t3), c(t2))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
