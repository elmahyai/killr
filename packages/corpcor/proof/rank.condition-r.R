
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(corpcor))
suppressPackageStartupMessages(library(jsonlite))
X <- matrix(c(
  1.2, 0.4, -0.2, 0.7,
  0.3, 1.1, 0.5, -0.4,
  -0.6, 0.2, 1.4, 0.1,
  0.8, -0.3, 0.2, 1.5,
  0.1, 0.9, -0.7, 0.3,
  -0.4, 0.6, 0.8, -0.2
), nrow = 6, byrow = TRUE)
M <- matrix(c(2, 0.4, 0.1, 0.4, 1.5, -0.2, 0.1, -0.2, 1.2), 3, 3, byrow = TRUE)
w <- c(0.1, 0.2, 0.05, 0.25, 0.15, 0.25)
json_val <- function(x) toJSON(as.numeric(x), auto_unbox = FALSE, digits = 17, na = "null")

one <- function() {
  rc <- rank.condition(M)
  c(rc$rank, rc$condition, rc$tol)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_val(value), median(elapsed) * 1000))
