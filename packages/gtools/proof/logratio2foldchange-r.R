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
  lr <- foldchange2logratio(foldchange(a, b))
  doc <- logratio2foldchange(lr)
  edge <- logratio2foldchange(c(-1, 0, 1, 2, NA_real_, -Inf, Inf))
  half <- logratio2foldchange(0.5)
  mat <- as.numeric(logratio2foldchange(matrix(c(-1, 0, 1, 2), nrow = 2)))
  recycle <- logratio2foldchange(c(1, 2, 3), base = c(2, 2, 10))
  ints <- logratio2foldchange(
    c(1L, NA_integer_, -1L),
    base = c(2L, 2L, 2L)
  )
  c(doc, edge, half, mat, recycle, ints)
}

value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', value, median(elapsed) * 1000))
