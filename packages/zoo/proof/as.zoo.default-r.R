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
  x <- as.zoo.default(c(4, 5))
  m <- as.zoo.default(matrix(1:4, nrow = 2), frequency = 1)
  q <- as.zoo.default(1:4, frequency = 4)
  big <- as.zoo.default(1:100000)
  c(
    as.numeric(coredata(x)), as.numeric(index(x)),
    as.numeric(coredata(m)), as.numeric(index(m)), frequency(m),
    as.numeric(index(q)), frequency(q),
    sum(as.numeric(coredata(big)))
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
