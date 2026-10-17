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
  set.seed(4242)
  x <- rdirichlet(20, c(1, 1, 1))
  main <- ddirichlet(x, c(1, 1, 1))
  extras <- c(
    ddirichlet(c(0.25, 0.25, 0.5), c(2, 2, 2)),
    ddirichlet(matrix(c(1, 0, 0), 1, 3), c(1, 2, 3)),
    ddirichlet(matrix(c(0, 0.5, 0.5), 1, 3), c(1, 1, 1)),
    ddirichlet(matrix(c(0.5, 0.6), 1, 2), c(2, 2)),
    ddirichlet(matrix(c(-0.1, 0.6, 0.5), 1, 3), c(1, 1, 1)),
    ddirichlet(matrix(c(0.5, 0.5), 1, 2), c(2, 2)),
    ddirichlet(
      matrix(c(0.3, 0.3, 0.4, 0.2, 0.5, 0.3), nrow = 2, byrow = TRUE),
      matrix(c(2, 2, 2, 3, 3, 3), nrow = 2, byrow = TRUE)
    )
  )
  c(main, extras)
}
value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(value), median(elapsed) * 1000))
