.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
one <- function() {
  a <- matrix(c(3, 5, 7, 2, 6, 4, 0, 2, 8), nrow = 3, byrow = TRUE)
  b <- matrix(seq(1, 12, 1), nrow = 3, byrow = TRUE)
  u <- c(0.25, -1.5, 2.75, 4)
  v <- matrix(seq(1, 6), nrow = 2, byrow = TRUE)
  c(
    entrywise.norm(a, 2),
    entrywise.norm(a, Inf),
    entrywise.norm(b, 1),
    entrywise.norm(u, 3),
    entrywise.norm(v, 1.5),
    entrywise.norm(1:4, 1),
    entrywise.norm(matrix(numeric(0), 0, 0), 2),
    entrywise.norm(numeric(0), 4)
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
