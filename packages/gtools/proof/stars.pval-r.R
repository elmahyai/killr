.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

flat_stars <- function(x) {
  paste(as.character(x), collapse = "|")
}

one <- function() {
  p <- c(
    0.0004, 0.0015, 0.013, 0.044, 0.067, 0.24,
    NA, 0, 0.001, 0.01, 0.05, 0.1, 1,
    1e-10, 0.000999999, 0.0010000001, 0.009999999, 0.0100000001
  )
  ex <- gtools::stars.pval(p)
  m <- matrix(c(0.001, 0.02, 0.06, 0.11), 2, 2)
  mx <- gtools::stars.pval(m)
  empty <- gtools::stars.pval(numeric(0))
  empty_mat <- gtools::stars.pval(matrix(numeric(0), 0, 3))
  c(
    flat_stars(ex),
    attr(ex, "legend"),
    flat_stars(mx),
    attr(mx, "legend"),
    flat_stars(empty),
    flat_stars(empty_mat),
    as.character(length(empty_mat))
  )
}

invisible(one())
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
payload <- paste(value, collapse = "§")
esc <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(payload), median(elapsed) * 1000))
