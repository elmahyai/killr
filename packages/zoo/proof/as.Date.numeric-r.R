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
  a <- as.numeric(as.Date.numeric(c(0, 1, -1), origin = "2000-01-01"))
  b <- as.numeric(as.Date.numeric(0, origin = "0000-00-00"))
  c <- as.numeric(as.Date.numeric(1, origin = "01/02/2000", format = "%d/%m/%Y"))
  d <- as.numeric(as.Date.numeric(0))
  big <- as.Date.numeric(0:99999, origin = "1970-01-01")
  c(a, b, c, d, sum(as.numeric(big)))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
