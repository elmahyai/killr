.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(matrixcalc))
if (as.character(packageVersion("matrixcalc")) != "1.0.6") stop("expected matrixcalc 1.0.6")
options(warn = -1)
flatten_e <- function(E) {
  parts <- numeric(0)
  for (i in seq_along(E)) {
    for (j in seq_along(E[[i]])) {
      parts <- c(parts, c(E[[i]][[j]]))
    }
  }
  parts
}
one <- function() {
  e3 <- E.matrices(3)
  e4 <- E.matrices(4)
  c(flatten_e(e3), flatten_e(e4))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
