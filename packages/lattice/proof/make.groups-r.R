.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(lattice))
if (packageDescription("lattice")$Version != "0.23-1") stop("expected lattice 0.23-1")
options(warn = -1)
uniform <- c(0.1, 0.2, 0.3)
exponential <- c(1, 2)
normal <- c(-1, 0, 1, 2)
one <- function() {
  g <- make.groups(uniform = uniform, exponential = exponential, normal = normal)
  c(as.numeric(g$data), as.integer(g$which))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = as.numeric(value), median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
