.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
one <- function() {
  d3 <- duplication.matrix(3)
  a <- matrix(c(1, 2, 3, 2, 3, 4, 3, 4, 5), nrow = 3, byrow = TRUE)
  vec_a <- vec(a)
  vech_a <- vech(a)
  y <- d3 %*% vech_a
  d4 <- duplication.matrix(4)
  c(c(d3), c(y), c(vec_a), c(d4))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
