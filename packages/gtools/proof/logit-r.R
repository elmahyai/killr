.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")
flat <- function(x) {
  if (is.null(x)) return("null")
  fmt <- function(v) if (is.na(v)) "NA" else sprintf("%.16g", as.numeric(v))
  if (is.matrix(x)) return(paste(c(nrow(x), ncol(x), vapply(as.numeric(x), fmt, "")), collapse = "|"))
  if (length(x) == 0) return("")
  paste(vapply(as.numeric(x), fmt, ""), collapse = "|")
}
esc <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s
}
one <- function() {
  x <- seq(0, 10, by = 0.25)
  xt <- logit(x, min = 0, max = 10)
  close <- logit(c(1e-16, 1 - 1e-16, .Machine$double.eps, 1 - .Machine$double.eps, 0.5))
  mat <- as.numeric(logit(matrix(c(0.2, 0.8, 0.4, 0.6), nrow = 2), min = c(0, 0.1), max = 1))
  recycled <- logit(c(0.2, 0.4, 0.6, 0.8), min = c(0, 0.1), max = 1)
  c(xt, close, mat, recycled)
}
value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(value), median(elapsed) * 1000))
