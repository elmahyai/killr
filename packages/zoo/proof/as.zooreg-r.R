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
  tser <- as.zooreg(ts(1:8, start = c(2000, 1), frequency = 4))
  over <- as.zooreg(ts(1:4, start = 2000, frequency = 4), frequency = 2)
  z <- as.zooreg(zoo(c(1, 2, 4), c(0, 2, 5)))
  big <- as.zooreg(ts(1:20000, start = 1, frequency = 1))
  c(
    as.numeric(coredata(tser)), as.numeric(index(tser)), frequency(tser),
    as.numeric(index(over)), frequency(over),
    as.numeric(coredata(z)), as.numeric(index(z)), frequency(z),
    sum(as.numeric(index(big)))
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
