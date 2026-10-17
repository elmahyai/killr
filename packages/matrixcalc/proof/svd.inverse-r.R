.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
flatten <- function(m) c(m)
one <- function() {
  a <- matrix(c(1, 2, 2, 1), nrow = 2, byrow = TRUE)
  b <- matrix(c(-1, 2, 2), nrow = 1, byrow = TRUE)
  c3 <- matrix(c(2, -1, -2, -4, 6, 3, -4, -2, 8), nrow = 3, byrow = TRUE)
  c_int <- matrix(1L:4L, 2, 2)
  d <- matrix(7)
  v <- c(1, 2, 3)
  big <- matrix(0, 64, 64)
  diag(big) <- (1:64) / 7
  c(
    flatten(svd.inverse(a)),
    flatten(svd.inverse(b)),
    flatten(svd.inverse(c3)),
    flatten(svd.inverse(c_int)),
    flatten(svd.inverse(d)),
    flatten(svd.inverse(v)),
    flatten(svd.inverse(big))
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
