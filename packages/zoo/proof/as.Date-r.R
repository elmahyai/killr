.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(zoo))
stopifnot(packageVersion("zoo") == "1.9-1")
json_num <- function(x) {
  if (length(x) == 0) return("[]")
  parts <- character(length(x))
  for (i in seq_along(x)) {
    parts[[i]] <- if (is.na(x[[i]])) "null" else sprintf("%.17g", x[[i]])
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
one <- function() {
  d0 <- as.numeric(as.Date(0))
  dv <- as.numeric(as.Date(c(0, 1, -1)))
  ch <- as.numeric(as.Date("2000-01-01"))
  dts <- as.numeric(as.Date(ts(1:4, start = 2000, frequency = 4)))
  big <- as.Date(0:99999)
  c(d0, dv, ch, dts, sum(as.numeric(big)))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
