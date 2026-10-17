.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0-6")
options(warn = -1)
flatten_t <- function(T) {
  parts <- numeric(0)
  for (i in seq_along(T)) {
    for (j in seq_along(T[[i]])) {
      parts <- c(parts, c(T[[i]][[j]]))
    }
  }
  parts
}
one <- function() {
  t3 <- T.matrices(3)
  t4 <- T.matrices(4)
  c(flatten_t(t3), flatten_t(t4))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
