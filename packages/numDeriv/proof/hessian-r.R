.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(numDeriv))

one <- function() {
  func <- function(x) x[1]^2 + 3 * x[1] * x[2] + x[2]^2
  as.numeric(hessian(func, c(1, 1)))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
