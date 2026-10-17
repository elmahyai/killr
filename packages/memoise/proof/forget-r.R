.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(memoise))
json_num <- function(x) {
  parts <- sprintf("%.17g", as.numeric(x))
  if (length(parts) == 1) return(parts[[1]])
  paste0("[", paste(parts, collapse = ","), "]")
}

one <- function() {
  n <- 0
  f <- function(x) { n <<- n + 1; x }
  m <- memoise(f)
  a <- m(1)
  cleared <- forget(m)
  b <- m(1)
  c(a, b, n, as.integer(cleared))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
