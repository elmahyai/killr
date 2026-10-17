.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(lattice))
if (packageDescription("lattice")$Version != "0.23-1") stop("expected lattice 0.23-1")
options(warn = -1)
one <- function() {
  x <- c(-1.2, 0.5, 0.5, 1.8, 3.1, 3.1, 5.0, -1.2, 2.4)
  z <- equal.count(x, number = 5, overlap = 0.4)
  lv <- do.call(rbind, levels(z))
  c(
    as.numeric(z),
    as.numeric(t(lv)),
    if (is.shingle(z)) 1 else 0,
    if (identical(as.shingle(z), z)) 1 else 0
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
