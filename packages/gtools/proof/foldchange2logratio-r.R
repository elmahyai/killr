.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

flat <- function(x) {
  if (is.null(x)) return("null")
  fmt <- function(v) {
    if (is.na(v)) return("NA")
    if (is.infinite(v)) return(if (v > 0) "Inf" else "-Inf")
    sprintf("%.16g", as.numeric(v))
  }
  if (is.matrix(x)) {
    return(paste(c(nrow(x), ncol(x), vapply(as.numeric(x), fmt, "")), collapse = "|"))
  }
  if (length(x) == 0) return("")
  paste(vapply(as.numeric(x), fmt, ""), collapse = "|")
}

one <- function() {
  a <- 1:21
  b <- 21:1
  f <- foldchange(a, b)
  doc <- logratio2foldchange(foldchange2logratio(f))
  edge <- foldchange2logratio(c(-2, -1, 0, 0.5, 1, 2, NA_real_, -Inf, Inf))
  above <- foldchange2logratio(c(2, 4, 8))
  below <- foldchange2logratio(c(-2, -4, -8))
  mat <- as.numeric(foldchange2logratio(matrix(c(-2, 0.5, 1, 2), nrow = 2)))
  recycle <- foldchange2logratio(c(2, 4, 8), base = c(2, 2, 10))
  ints <- foldchange2logratio(
    c(2L, NA_integer_, -2L),
    base = c(2L, 2L, 2L)
  )
  c(foldchange2logratio(f), doc, edge, above, below, mat, recycle, ints)
}

value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', value, median(elapsed) * 1000))
