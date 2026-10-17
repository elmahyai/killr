.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(lattice))
if (packageDescription("lattice")$Version != "0.23-1") stop("expected lattice 0.23-1")
options(warn = -1)
one <- function() {
  x <- c(4.5, 2.1, 4.5, 7.8, 2.1)
  intervals <- matrix(c(2.0, 3.0, 4.0, 5.0, 7.0, 8.0), ncol = 2, byrow = TRUE)
  s <- shingle(x, intervals = intervals)
  lv <- do.call(rbind, levels(s))
  c(
    as.numeric(s),
    as.numeric(t(lv)),
    if (is.shingle(s)) 1 else 0,
    if (identical(as.shingle(s), s)) 1 else 0
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = as.numeric(value), median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
