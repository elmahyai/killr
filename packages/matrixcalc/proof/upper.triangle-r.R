.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
one <- function() {
  a <- matrix(seq(1, 16, 1), nrow = 4, byrow = TRUE)
  b <- matrix(
    c(0.1, -1.5, 2.25, 4, 0.5, -0.25, 8, 3, 1.125),
    nrow = 3,
    byrow = TRUE
  )
  d <- matrix(0, 64, 64)
  diag(d) <- (1:64) / 7
  e <- matrix(1:9, nrow = 3)
  f <- matrix(
    c(TRUE, FALSE, TRUE, FALSE, TRUE, FALSE, TRUE, FALSE, TRUE),
    nrow = 3
  )
  parts <- list(
    c(upper.triangle(a)),
    c(upper.triangle(b)),
    c(upper.triangle(matrix(3.5))),
    c(upper.triangle(matrix(numeric(0), 0, 0))),
    c(upper.triangle(d)),
    c(upper.triangle(e)),
    c(upper.triangle(f))
  )
  unlist(parts)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
