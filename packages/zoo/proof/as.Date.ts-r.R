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
  q <- as.numeric(as.Date.ts(ts(1:4, start = 2000, frequency = 4)))
  q2 <- as.numeric(as.Date.ts(ts(1:3, start = c(2000, 2), frequency = 4)))
  m <- as.numeric(as.Date.ts(ts(1:3, start = c(2000, 2), frequency = 12)))
  a <- as.numeric(as.Date.ts(ts(1:3, start = 1999, frequency = 1)))
  off <- as.numeric(as.Date.ts(ts(1:3, start = c(1999, 11), frequency = 12), offset = 1))
  big <- as.Date.ts(ts(1:5000, start = 2000, frequency = 12))
  msg <- tryCatch(
    as.Date.ts(ts(1:3, start = 2000, frequency = 7)),
    error = function(e) conditionMessage(e)
  )
  bad <- if (identical(msg, "unable to convert ts time to Date class")) 1 else 0
  c(q, q2, m, a, off, sum(as.numeric(big)), bad)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
