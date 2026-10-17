.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(progressr)
options(progressr.enable = TRUE)

one <- function() {
  value <- slow_sqrt(c(1, 4, 9), delay = 0)
  as.numeric(value)
}

ans <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(sprintf("%.17g", ans), collapse = ","),
  median(elapsed) * 1000
))
