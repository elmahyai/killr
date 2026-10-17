.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
f <- function(t, y, parms) {
  dy1 <- -0.04 * y[1] + 1e4 * y[2] * y[3]
  dy2 <- 0.04 * y[1] - 1e4 * y[2] * y[3] - 3e7 * y[2]^2
  dy3 <- 3e7 * y[2]^2
  list(c(dy1, dy2, dy3))
}
one <- function() {
  radau(c(1, 0, 0), seq(0, 40, 10), f, NULL)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
