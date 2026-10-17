.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(ordinal))

one <- function() {
  pgumbel(c(-1, 0, 1), max = FALSE, lower.tail = FALSE)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
