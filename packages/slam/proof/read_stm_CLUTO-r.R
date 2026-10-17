.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(slam))

one <- function() {
  f <- tempfile()
  writeLines(c("2 2 3", "1 1.5 2 3", "1 2"), f)
  as.numeric(as.matrix(read_stm_CLUTO(f)))
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
