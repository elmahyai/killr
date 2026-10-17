.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(progressr)
options(progressr.enable = TRUE)

one <- function() {
  value <- slow_sum(1:10, delay = 0)
  list(value = as.numeric(value), storage = storage.mode(value))
}

ans <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":%.17g,"storage":"%s","median_ms":%.17g}\n',
  ans$value, ans$storage, median(elapsed) * 1000
))
