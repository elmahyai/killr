.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
one <- function() {
  k34 <- K.matrix(3, 4)
  k22 <- K.matrix(2, 2)
  k33 <- K.matrix(3)
  a <- matrix(seq(1, 12, 1), nrow = 3, byrow = TRUE)
  vec_a <- vec(a)
  vec_at <- vec(t(a))
  c(
    c(k34),
    c(k22),
    c(k33),
    c(k34 %*% vec_a),
    c(vec_at)
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
