.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
one <- function() {
  a <- matrix(seq(1, 16, 1), nrow = 4, byrow = TRUE)
  b <- matrix(c(0.1, -1.5, 2.25, 4, 0.5, -0.25, 8, 3, 1.125), nrow = 3, byrow = TRUE)
  c <- matrix(1:12, nrow = 3, ncol = 4)
  d <- matrix(0, 5, 7)
  diag(d) <- (1:5) / 3
  e <- matrix(numeric(0), 0, 4)
  f <- matrix(3.5, 1, 1)
  c(
    c(vec(a)),
    c(vec(b)),
    c(vec(c)),
    c(vec(d)),
    c(vec(e)),
    c(vec(f))
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
