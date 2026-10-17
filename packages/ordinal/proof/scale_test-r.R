.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(ordinal))

one <- function() {
  data(wine)
  fm <- clm(rating ~ contact + temp, data = wine)
  st <- scale_test(fm)
  as.numeric(unlist(st))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
fmt <- function(x) if (is.na(x)) "null" else sprintf("%.17g", x)
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(vapply(value, fmt, character(1)), collapse = ","),
  median(elapsed) * 1000
))
