.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(abind))
if (packageDescription("abind")$Version != "1.4-8") stop("expected abind 1.4-8")

one <- function() {
  x <- array(1:24, dim = c(2, 3, 4))
  y <- array(seq_len(prod(1:8)), dim = 1:8)
  parts <- list(
    asub(x, 1, 1, drop = FALSE),
    asub(x, list(1:2, 3:4), c(1, 3)),
    asub(x, list(1:2, 2, 1:2), c(1, 2, 3)),
    asub(y, 1, 1),
    asub(y, 1, 2),
    asub(y, 1, 3),
    asub(y, 1, 3, drop = FALSE),
    asub(y, list(1, 1), c(3, 5), drop = FALSE),
    asub(y, list(1, 1), c(3, 5))
  )
  out <- c()
  for (part in parts) {
    d <- dim(part)
    if (is.null(d)) d <- length(part)
    out <- c(out, d, as.numeric(part))
  }
  out
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17))
