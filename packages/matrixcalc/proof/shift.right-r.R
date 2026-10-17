.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0.6")
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
  parts <- list(
    c(shift.right(a, 1)),
    c(shift.right(a, 3)),
    c(shift.right(a, 0)),
    c(shift.right(a, 2, fill = -1.5)),
    c(shift.right(b, 1, fill = 99)),
    c(shift.right(matrix(1:6, 2, 3), 2)),
    c(shift.right(matrix(numeric(0), 0, 0), 0)),
    c(shift.right(d, 5)),
    c(shift.right(e, 10, fill = 0.25))
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
