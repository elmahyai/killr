.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
one <- function() {
  x <- matrix(seq(1, 4))
  y <- matrix(seq(5, 8))
  a <- matrix(seq(1, 6), nrow = 2, byrow = TRUE)
  b <- matrix(seq(11, 16), nrow = 2, byrow = TRUE)
  u <- c(0.25, -1.5, 2)
  v <- c(4, 0.5, -0.125)
  m <- matrix(c(0.1, -1.5, 2.25, 4, 0.5, -0.25), nrow = 3, byrow = TRUE)
  w <- c(9, 8, 7, 6)
  s <- matrix(c(1, 2, 3, 4), nrow = 2, byrow = TRUE)
  parts <- list(
    c(x %s% y),
    c(a %s% b),
    c(u %s% v),
    c(matrix(1:2, nrow = 1) %s% matrix(3:4, nrow = 1)),
    c(m %s% w),
    c(2.5 %s% s)
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
