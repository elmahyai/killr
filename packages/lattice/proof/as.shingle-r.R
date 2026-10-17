.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(lattice))
if (packageDescription("lattice")$Version != "0.23-1") stop("expected lattice 0.23-1")
options(warn = -1)
one <- function() {
  x <- c(4.5, 2.1, 4.5, 7.8, 2.1)
  s <- as.shingle(x)
  s2 <- as.shingle(s)
  lv <- do.call(rbind, levels(s))
  c(as.numeric(s), as.numeric(t(lv)), as.numeric(s2), if (identical(s, s2)) 1 else 0)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = as.numeric(value), median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
