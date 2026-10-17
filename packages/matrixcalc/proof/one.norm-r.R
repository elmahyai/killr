.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
one <- function() {
  a <- matrix(c(3, 5, 7, 2, 6, 4, 0, 2, 8), nrow = 3, byrow = TRUE)
  b <- matrix(seq(1, 16, 1), nrow = 4, byrow = TRUE)
  v <- 1:12
  c(
    one.norm(a),
    one.norm(b),
    one.norm(v),
    one.norm(matrix(3.5)),
    one.norm(matrix(numeric(0), 0, 0)),
    one.norm(matrix(c(0.1, -1.5, 2.25, 4, 0.5, -0.25, 8, 3, 1.125), nrow = 3, byrow = TRUE))
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
