.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

flat <- function(x) {
  if (is.null(x)) return("null")
  fmt <- function(v) {
    if (is.na(v)) return("NA")
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
  doc <- foldchange(a, b)
  edge <- foldchange(c(1, 2, NA_real_, 0, 0), c(2, 1, 1, 0, 1))
  mat <- as.numeric(foldchange(matrix(1:4, nrow = 2), matrix(4:1, nrow = 2)))
  recycle <- foldchange(1:5, 3)
  ints <- foldchange(c(1L, NA_integer_, 3L), c(2L, 1L, 3L))
  c(doc, edge, mat, recycle, ints)
}

value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', value, median(elapsed) * 1000))
